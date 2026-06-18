"""Клавиатуры бота. Подписи кнопок держим тут, чтобы не плодить магические строки.

Всё управление — через кнопки меню, без команд. Единственная команда — /start,
и та нужна только чтобы запустить бота.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ——— клиентское меню ———
BTN_ASK = "💬 Задать вопрос"
BTN_SERVICES = "💅 Услуги и цены"
BTN_CONTACTS = "📍 Контакты"
BTN_OPERATOR = "📞 Связаться с администратором"

# ——— админ-панель ———
BTN_STATS = "📊 Статистика"
BTN_REQUESTS = "📥 Обращения"
BTN_REINDEX = "🔄 Обновить базу"
BTN_TOPICS = "📚 Темы базы"
BTN_CLIENT_MODE = "👤 Режим клиента"


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ASK)],
            [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_CONTACTS)],
            [KeyboardButton(text=BTN_OPERATOR)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос или отправьте голосовое…",
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_REQUESTS)],
            [KeyboardButton(text=BTN_REINDEX), KeyboardButton(text=BTN_TOPICS)],
            [KeyboardButton(text=BTN_CLIENT_MODE)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Админ-панель — выберите действие…",
    )


def call_operator_kb() -> InlineKeyboardMarkup:
    # эту кнопку подставляем под ответ, когда бот не уверен
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👩‍💼 Позвать администратора", callback_data="call_operator")]
        ]
    )
