"""Админ-панель на кнопках.

Доступ только у ID из ADMIN_IDS. Роутер фильтруется AdminFilter — он же
пропускает админа дальше к обычным вопросам, когда включён «Режим клиента».
"""
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from app import keyboards as kb
from app.rag import indexer
from app.rag.store import KnowledgeBase
from app.services.gemini import Gemini
from app.services.stats import Stats

router = Router()

# админы, которые временно «прикинулись клиентом» (чтобы протестить бота)
_client_mode: set[int] = set()


def enter_client_mode(uid: int) -> None:
    _client_mode.add(uid)


def exit_client_mode(uid: int) -> None:
    _client_mode.discard(uid)


def in_client_mode(uid: int) -> bool:
    return uid in _client_mode


class AdminFilter(BaseFilter):
    """Пускаем только админов и только когда они не в «режиме клиента»."""

    def __init__(self, admin_ids: set[int]) -> None:
        self.admin_ids = set(admin_ids)

    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        return bool(user) and user.id in self.admin_ids and user.id not in _client_mode


@router.message(F.text == kb.BTN_STATS)
async def show_stats(message: Message, stats: Stats) -> None:
    s = await stats.summary()
    rate = (s["answered"] / s["total"] * 100) if s["total"] else 0
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"Всего вопросов: <b>{s['total']}</b>\n"
        f"Ответил сам: <b>{s['answered']}</b> ({rate:.0f}%)\n"
        f"Передано админу: <b>{s['handoffs']}</b>\n"
        f"Уникальных пользователей: <b>{s['users']}</b>\n"
        f"За последние 7 дней: <b>{s['last7']}</b>"
    )


@router.message(F.text == kb.BTN_REQUESTS)
async def show_requests(message: Message, stats: Stats) -> None:
    rows = await stats.recent_handoffs(10)
    if not rows:
        await message.answer("Пока ни одного обращения к администратору 👍")
        return
    lines = ["📥 <b>Последние обращения</b>\n"]
    for ts, username, question in rows:
        when = datetime.fromtimestamp(ts).strftime("%d.%m %H:%M")
        lines.append(f"• {when} — {username or '—'}: {question or '—'}")
    await message.answer("\n".join(lines))


@router.message(F.text == kb.BTN_TOPICS)
async def show_topics(message: Message) -> None:
    topics = indexer.list_topics()
    body = "\n".join(f"• {t}" for t in topics) or "База пустая."
    await message.answer(f"📚 <b>Темы базы знаний</b>\n\n{body}")


@router.message(F.text == kb.BTN_REINDEX)
async def reindex(message: Message, gemini: Gemini, kbase: KnowledgeBase) -> None:
    note = await message.answer("⏳ Пересобираю базу знаний…")
    try:
        count = await indexer.build_index(gemini)
        kbase.reload()  # подхватываем свежий индекс без перезапуска
        await note.edit_text(f"✅ Готово. В базе {count} кусочков, индекс обновлён.")
    except Exception as e:
        await note.edit_text(f"⚠️ Не смог пересобрать базу: {e}")


@router.message(F.text == kb.BTN_CLIENT_MODE)
async def client_mode(message: Message) -> None:
    enter_client_mode(message.from_user.id)
    await message.answer(
        "Вы в режиме клиента — можно проверить бота как обычный пользователь.\n"
        "Вернуться в админ-панель — /start",
        reply_markup=kb.client_menu(),
    )
