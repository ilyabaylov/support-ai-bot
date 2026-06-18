import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

# Загружаем токен
load_dotenv(r"c:\Users\baylo\Downloads\supportai\supportai\.env")
token = os.getenv("BOT_TOKEN")

if not token:
    print("Ошибка: BOT_TOKEN не найден в .env")
    exit(1)

bot = Bot(token=token)
dp = Dispatcher()

# Храним текущий шаг диалога для каждого пользователя
user_steps = {}

RESPONSES = {
    0: (
        "Привет! 💎 Я Аружан, администратор Lumière.\n\n"
        "Могу сориентировать по ценам, свободным окошкам или подсказать адрес. "
        "Пишите прямо сюда текстом или отправляйте голосовое — я всё пойму! 🌸"
    ),
    1: (
        "Привет! Мы в самом центре — ул. Гоголя 86, угол Панфилова (2 этаж). "
        "Ориентир — Арбат и ЦУМ, от метро буквально 5 минут пешком.\n\n"
        "Парковка есть, городская платная прямо вдоль Панфилова. Ждём вас! 🚗"
    ),
    2: (
        "Маникюр с покрытием гель-лаком у нас стоит 10 000 ₸. В эту стоимость уже входит выравнивание.\n\n"
        "Вас записать на процедуру? 😊"
    ),
    3: (
        "Отлично, Илья, спасибо! Передала ваши данные старшему администратору, "
        "он сейчас свяжется с вами для подтверждения точного времени. Хорошего дня! 👍"
    )
}

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    user_steps[uid] = 0
    await message.answer(RESPONSES[0])
    user_steps[uid] = 1

@dp.message(F.text)
async def handle_message(message: Message):
    uid = message.from_user.id
    step = user_steps.get(uid, 0)
    
    # Если шаг вышел за рамки сценария, сбрасываем на старт
    if step not in RESPONSES or step == 0:
        step = 0
        user_steps[uid] = 1
        await message.answer(RESPONSES[0])
        return

    # Отправляем имитацию "печатает..." на 1 секунду для реалистичности
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(1.2)
    
    await message.answer(RESPONSES[step])
    user_steps[uid] = step + 1

async def main():
    print("==================================================")
    print("ЗАПУЩЕН ИМИТАТОР БОТА (MOCK BOT)")
    print("Запросы к Gemini API отключены. Лимиты не расходуются.")
    print("==================================================")
    
    # Удаляем вебхуки и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
