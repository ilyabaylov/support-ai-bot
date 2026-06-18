"""/start и клиентское меню.

Отдельно ветвим на админа и клиента: админ на /start получает админ-панель.
Вся навигация — кнопками, без команд.
"""
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import content
from app import dialog
from app import keyboards as kb
from app.config import Config
from app.handlers import admin
from app.handlers.ask import answer_question
from app.handlers.operator import notify_operator
from app.rag.store import KnowledgeBase
from app.services import stats as st
from app.services.gemini import Gemini
from app.services.stats import Stats

router = Router()


@router.message(CommandStart())
async def start(message: Message, cfg: Config) -> None:
    uid = message.from_user.id
    admin.exit_client_mode(uid)  # /start всегда возвращает админа в админ-панель
    dialog.reset(uid)            # начинаем разговор с чистого листа
    # Временно отключено для теста клиента:
    # if uid in cfg.admin_ids:
    #     await message.answer(
    #         "🛠 Админ-панель. Выберите действие ниже 👇",
    #         reply_markup=kb.admin_menu(),
    #     )
    #     return
    await message.answer(content.WELCOME, reply_markup=kb.client_menu())


@router.message(F.text == kb.BTN_ASK)
async def ask_hint(message: Message) -> None:
    await message.answer(content.ASK_HINT)


@router.message(F.text == kb.BTN_CONTACTS)
async def contacts(message: Message) -> None:
    await message.answer(content.CONTACTS)


@router.message(F.text == kb.BTN_SERVICES)
async def services(
    message: Message,
    bot: Bot,
    cfg: Config,
    gemini: Gemini,
    kbase: KnowledgeBase,
    stats: Stats,
) -> None:
    # кнопка «Услуги и цены» — тот же мозг, что и любой вопрос
    await answer_question(
        message, content.PRESET_SERVICES, cfg=cfg, gemini=gemini, kbase=kbase, stats=stats, bot=bot
    )


@router.message(F.text == kb.BTN_OPERATOR)
async def call_operator(message: Message, bot: Bot, cfg: Config, stats: Stats) -> None:
    await notify_operator(
        bot, cfg, message.from_user, "Нажал «Связаться с администратором»"
    )
    await stats.log(
        user_id=message.from_user.id,
        username=(f"@{message.from_user.username}" if message.from_user.username else f"id {message.from_user.id}"),
        kind=st.HANDOFF,
        question="Нажал «Связаться с администратором»",
    )
    await message.answer(
        "Передал администратору — с вами скоро свяжутся 👌\n"
        f"А если срочно — WhatsApp/звонок: {content.PHONE}"
    )
