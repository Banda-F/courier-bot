import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не задан")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL не задан")

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class CourierForm(StatesGroup):
    name = State()
    city = State()
    age = State()
    experience = State()
    transport = State()
    ready_date = State()
    phone = State()

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

async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    print(f"✅ Webhook установлен на {WEBHOOK_URL}/webhook")

async def health(request):
    return web.Response(text="Bot is running")

def main():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path="/webhook")

    app.on_startup.append(lambda _: on_startup())
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
