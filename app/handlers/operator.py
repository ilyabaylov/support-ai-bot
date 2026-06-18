"""Передача диалога живому администратору.

Шлём уведомление в operator_target (явный OPERATOR_CHAT_ID или первый из ADMIN_IDS).
Если никого нет (например, на этапе разработки) — просто пишем в лог, бот не падает.
"""
import html
import logging

from aiogram import Bot
from aiogram.types import User

from app.config import Config

logger = logging.getLogger(__name__)


async def notify_operator(bot: Bot, cfg: Config, user: User, question: str) -> None:
    username = f"@{user.username}" if user.username else f"id {user.id}"
    text = (
        "🔔 <b>Нужен администратор</b>\n"
        f"От: {html.escape(username)} ({html.escape(user.full_name)})\n"
        f"Контекст: {html.escape(question)}"
    )
    target = cfg.operator_target
    if target:
        try:
            await bot.send_message(target, text)
        except Exception as e:  # вдруг админ ещё не нажал /start у бота
            logger.warning("Не смог уведомить администратора: %s", e)
    else:
        logger.info("Адресат не задан (ADMIN_IDS/OPERATOR_CHAT_ID). Сообщение: %s", text)
