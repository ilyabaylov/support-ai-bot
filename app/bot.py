"""Точка входа.

Поднимаем бота, грузим базу знаний и кладём зависимости в диспетчер —
aiogram сам прокинет их в хендлеры по именам аргументов.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import load_config
from app.handlers import admin, ask, common
from app.rag.store import KnowledgeBase
from app.services.gemini import Gemini
from app.services.stats import Stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _set_commands(bot: Bot) -> None:
    # намеренно только /start: всё остальное живёт на кнопках меню
    await bot.set_my_commands([BotCommand(command="start", description="Запустить")])


async def main() -> None:
    cfg = load_config()

    stats = Stats()
    await stats.init()

    # база знаний должна быть собрана заранее: python -m scripts.build_index
    kbase = KnowledgeBase.load()
    gemini = Gemini(cfg.gemini_api_key, cfg.chat_model, cfg.embed_model)

    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # зависимости в диспетчер — прилетят в хендлеры по именам
    dp = Dispatcher(cfg=cfg, gemini=gemini, kbase=kbase, stats=stats)

    # админ-роутер видят только админы (и только вне «режима клиента»)
    # Временно отключено для теста клиента:
    # admin.router.message.filter(admin.AdminFilter(cfg.admin_ids))

    # порядок важен: common ловит /start и клиентские кнопки,
    # admin — кнопки админки, ask — любой оставшийся вопрос (текст/голос)
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(ask.router)

    await _set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен (база: %d кусочков), начинаю polling…", len(kbase))
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлено вручную")
