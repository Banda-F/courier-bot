import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    raise ValueError("Проверьте .env: BOT_TOKEN и ADMIN_CHAT_ID должны быть заданы")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния анкеты
class CourierForm(StatesGroup):
    name = State()
    city = State()
    age = State()
    experience = State()
    transport = State()
    ready_date = State()
    phone = State()

# Клавиатуры
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 Оставить заявку")]],
    resize_keyboard=True
)
phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚴‍♂️ Привет! Оставь заявку, и мы поможем тебе начать увеличивать доход с доставкой.",
        reply_markup=start_kb
    )

@dp.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(CourierForm.name)
    await message.answer("Как вас зовут?", reply_markup=ReplyKeyboardRemove())

@dp.message(CourierForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(CourierForm.city)
    await message.answer("Из какого вы города?")

@dp.message(CourierForm.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(CourierForm.age)
    await message.answer("Сколько вам лет?")

@dp.message(CourierForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число (только цифры).")
        return
    await state.update_data(age=message.text)
    await state.set_state(CourierForm.experience)
    await message.answer("Есть ли у вас опыт выполнения доставок?")

@dp.message(CourierForm.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text.strip())
    await state.set_state(CourierForm.transport)
    await message.answer("На каком транспорте вы можете выполнять доставки?")

@dp.message(CourierForm.transport)
async def process_transport(message: types.Message, state: FSMContext):
    await state.update_data(transport=message.text.strip())
    await state.set_state(CourierForm.ready_date)
    await message.answer("Когда готовы начать? (например: 'с понедельника', 'завтра')")

@dp.message(CourierForm.ready_date)
async def process_ready_date(message: types.Message, state: FSMContext):
    await state.update_data(ready_date=message.text.strip())
    await state.set_state(CourierForm.phone)
    await message.answer(
        "Поделитесь номером телефона, нажав на кнопку:",
        reply_markup=phone_kb
    )

@dp.message(CourierForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    data = await state.get_data()

    report = (
        "📋 *Новая заявка на курьера!*\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"📦 Опыт: {data['experience']}\n"
        f"🚲 Транспорт: {data['transport']}\n"
        f"📅 Готов начать: {data['ready_date']}\n"
        f"📞 Телефон: {phone}"
    )
    await bot.send_message(ADMIN_CHAT_ID, report, parse_mode="Markdown")
    await message.answer(
        "✅ Спасибо! Мы свяжемся с тобой в течение дня.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@dp.message(CourierForm.phone)
async def process_phone_text(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, используйте кнопку '📱 Отправить номер'.",
        reply_markup=phone_kb
    )

async def main():
    print("Бот @rabota_curierom_bot запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())