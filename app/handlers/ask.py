"""Главная логика — «мозг» администратора.

Принимаем сообщение (текстом или голосом), подмешиваем факты из базы знаний
как опору (не как шлагбаум), помним контекст разговора и отвечаем живым диалогом
со стримингом. Живого администратора зовём только когда это реально нужно
(запись готова / жалоба) — по служебному тегу [[HANDOFF]] от модели.
"""
import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message, User

from app import content
from app import dialog
from app import keyboards as kb
from app.config import Config
from app.handlers.operator import notify_operator
from app.rag.store import KnowledgeBase
from app.services import stats as st
from app.services.gemini import Gemini
from app.services.stats import Stats

logger = logging.getLogger(__name__)
router = Router()

# как часто обновляем сообщение при стриминге (раз в N накопленных символов)
_EDIT_EVERY = 60

# служебный тег: модель ставит его, когда пора подключить живого администратора
HANDOFF_TAG = "[[HANDOFF]]"

SYSTEM_TEMPLATE = (
    "{persona}\n\n"
    "ЧТО МЫ ЗНАЕМ (база салона, твой источник правды):\n{context}"
)


def _uname(user: User | None) -> str:
    if not user:
        return "неизвестно"
    return f"@{user.username}" if user.username else f"id {user.id}"


async def answer_question(
    message: Message,
    question: str,
    *,
    cfg: Config,
    gemini: Gemini,
    kbase: KnowledgeBase,
    stats: Stats,
    bot: Bot,
) -> None:
    question = (question or "").strip()
    user = message.from_user
    uid = user.id if user else 0
    if not question:
        await message.answer("Не разобрал сообщение, повторите, пожалуйста 🙏")
        return

    # 1. подбираем релевантные куски базы как опору (не как шлагбаум!)
    best_score = 0.0
    context = ""
    try:
        q_vec = await gemini.embed_one(question)
        found = kbase.search(q_vec, cfg.top_k)
        best_score = found[0][0] if found else 0.0
        context = "\n\n---\n\n".join(chunk for _, chunk in found)
    except Exception as e:
        logger.warning("Не смог посчитать эмбеддинг/поиск: %s", e)

    if not context:
        context = "(по этому вопросу в базе нет прямых данных)"
    if best_score < cfg.sim_threshold:
        # мягкая подсказка модели: точных данных нет — веди себя аккуратно, но не отказывай
        context = (
            "⚠️ По этому вопросу в базе нет точных данных — отвечай общими словами, "
            "не выдумывай цифры, при необходимости предложи уточнить у мастера.\n\n" + context
        )

    system = SYSTEM_TEMPLATE.format(persona=content.PERSONA, context=context)
    history = dialog.history(uid)

    # 2. стримим ответ, постепенно редактируя одно сообщение
    placeholder = await message.answer("✉️…")
    buffer = ""
    last_len = 0
    try:
        async for piece in gemini.chat_stream(system, history, question):
            buffer += piece
            visible = buffer.replace(HANDOFF_TAG, "")
            if len(visible) - last_len >= _EDIT_EVERY:
                last_len = len(visible)
                try:
                    # parse_mode=None: на полпути разметка может быть битой, телега ругается
                    await placeholder.edit_text(visible or "✉️…", parse_mode=None)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("Gemini не ответил: %s", e)
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
            text_to_send = (
                "Ой, я получил слишком много вопросов подряд и мне нужно немного передохнуть 🌸\n\n"
                "Пожалуйста, повторите ваш вопрос через 30-40 секунд или напишите администратору напрямую 👇"
            )
        else:
            text_to_send = (
                "Связь на секунду прервалась 🙈 Повторите вопрос, пожалуйста, "
                "или напишите администратору напрямую 👇"
            )
        try:
            await placeholder.edit_text(
                text_to_send,
                reply_markup=kb.call_operator_kb(),
            )
        except Exception:
            pass
        return

    raw = buffer.strip()
    needs_human = HANDOFF_TAG in raw
    answer = raw.replace(HANDOFF_TAG, "").strip()
    if not answer:
        answer = "Уточните, пожалуйста, чуть подробнее — и я помогу 🙌"

    try:
        await placeholder.edit_text(answer, parse_mode=None)
    except Exception as e:
        logger.debug("Placeholder final edit skipped/failed: %s", e)

    # 3. запоминаем реплики, чтобы держать контекст разговора
    dialog.remember(uid, "user", question)
    dialog.remember(uid, "model", answer)

    # 4. статистика + передача администратору, если бот сам решил
    kind = st.ANSWERED
    if needs_human:
        kind = st.NO_ANSWER
    elif best_score < cfg.sim_threshold:
        kind = st.LOW_CONFIDENCE

    await stats.log(
        user_id=uid or None,
        username=_uname(user),
        kind=kind,
        score=best_score,
        question=question,
    )
    if needs_human:
        await stats.log(
            user_id=uid or None,
            username=_uname(user),
            kind=st.HANDOFF,
            question=question,
        )
        await notify_operator(
            bot, cfg, user, f"Диалог требует администратора. Последнее сообщение: {question}"
        )
        await message.answer(
            f"Передаю администратору — свяжется с вами в ближайшее время 💬\n"
            f"Если срочно — WhatsApp/звонок: {content.PHONE}"
        )


@router.message(F.voice)
async def on_voice(
    message: Message,
    bot: Bot,
    cfg: Config,
    gemini: Gemini,
    kbase: KnowledgeBase,
    stats: Stats,
) -> None:
    # скачиваем голосовое в память и отдаём в Gemini на расшифровку
    buf = BytesIO()
    await bot.download(message.voice, destination=buf)
    try:
        text = await gemini.transcribe_voice(buf.getvalue())
    except Exception as e:
        logger.warning("Не смог расшифровать голос: %s", e)
        text = ""
    if text:
        await message.answer(f"🎤 Услышал: <i>{text}</i>")
    await answer_question(
        message, text, cfg=cfg, gemini=gemini, kbase=kbase, stats=stats, bot=bot
    )


@router.message(F.text)
async def on_text(
    message: Message,
    bot: Bot,
    cfg: Config,
    gemini: Gemini,
    kbase: KnowledgeBase,
    stats: Stats,
) -> None:
    await answer_question(
        message, message.text, cfg=cfg, gemini=gemini, kbase=kbase, stats=stats, bot=bot
    )


@router.callback_query(F.data == "call_operator")
async def on_call_operator(call: CallbackQuery, bot: Bot, cfg: Config, stats: Stats) -> None:
    await notify_operator(bot, cfg, call.from_user, "Нажал «Позвать администратора»")
    await stats.log(
        user_id=call.from_user.id,
        username=_uname(call.from_user),
        kind=st.HANDOFF,
        question="Нажал «Позвать администратора»",
    )
    await call.message.answer("Передал администратору — скоро напишет 👌")
    await call.answer()
