import os
import json
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

# Загрузка переменных окружения
load_dotenv()

# --- Обязательные переменные ---
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

# --- Необязательные переменные для Google Sheets ---
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния анкеты ---
class CourierForm(StatesGroup):
    name = State()
    city = State()
    age = State()
    experience = State()
    transport = State()
    ready_date = State()
    phone = State()

# --- Клавиатуры ---
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 Оставить заявку")]],
    resize_keyboard=True
)
phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# --- Приветствие ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚀 *Привет! Стань курьером Яндекс Еды и зарабатывай когда удобно.*\n\n"
        "Мы — официальный партнёр, поможем быстро выйти на линию.\n\n"
        "💰 *Доход:* от 4 000 ₽ в день + 100% чаевых.\n"
        "🕒 *График:* сам выбираешь смены (хоть 2 часа в день).\n"
        "🎓 *Опыт:* не нужен — всему научим.\n"
        "🚲 *Транспорт:* пешком, вело, самокат, авто.\n\n"
        "📝 *Заполни анкету — это займёт 2 минуты.*",
        reply_markup=start_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(CourierForm.name)
    await message.answer(
        "👤 *Как к вам обращаться?* (Имя или никнейм)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

@dp.message(CourierForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(CourierForm.city)
    await message.answer(
        "🌆 *В каком городе планируете работать?*",
        parse_mode="Markdown"
    )

@dp.message(CourierForm.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(CourierForm.age)
    await message.answer(
        "🎂 *Сколько вам лет?* (только цифры)",
        parse_mode="Markdown"
    )

@dp.message(CourierForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (только цифры).")
        return
    await state.update_data(age=message.text)
    await state.set_state(CourierForm.experience)
    await message.answer(
        "📦 *Был ли у вас опыт в доставке?* (Можно написать «Да, немного» или «Нет, первый раз»)",
        parse_mode="Markdown"
    )

@dp.message(CourierForm.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text.strip())
    await state.set_state(CourierForm.transport)
    await message.answer(
        "🚗 *Какой транспорт будете использовать?* (пешком, велосипед, самокат, авто – или свой вариант)",
        parse_mode="Markdown"
    )

@dp.message(CourierForm.transport)
async def process_transport(message: types.Message, state: FSMContext):
    await state.update_data(transport=message.text.strip())
    await state.set_state(CourierForm.ready_date)
    await message.answer(
        "📅 *Когда сможете выйти на первую смену?* (например: «с завтрашнего дня», «через неделю», «после 20 мая»)",
        parse_mode="Markdown"
    )

@dp.message(CourierForm.ready_date)
async def process_ready_date(message: types.Message, state: FSMContext):
    await state.update_data(ready_date=message.text.strip())
    await state.set_state(CourierForm.phone)
    await message.answer(
        "📱 *Поделитесь номером телефона* – нажмите кнопку ниже.",
        reply_markup=phone_kb,
        parse_mode="Markdown"
    )

@dp.message(CourierForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    data = await state.get_data()

    # --- Отправка админу в Telegram ---
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

    # --- Запись в Google Sheets (если настроено) ---
    if GOOGLE_CREDENTIALS and SPREADSHEET_ID:
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials

            creds_dict = json.loads(GOOGLE_CREDENTIALS)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1

            row = [
                data['name'], data['city'], data['age'],
                data['experience'], data['transport'],
                data['ready_date'], phone
            ]
            sheet.append_row(row)
            print(f"✅ Добавлена строка в Google Sheets: {data['name']}")
        except Exception as e:
            print(f"❌ Ошибка записи в Google Sheets: {e}")

    # --- Финальное сообщение ---
    await message.answer(
        "✅ *Спасибо! Анкета принята.*\n\n"
        "В ближайшие часы с вами свяжется менеджер в Telegram или по телефону, чтобы:\n"
        "• подтвердить детали\n"
        "• помочь оформить самозанятость\n"
        "• отправить ссылку на регистрацию в Яндекс Еде\n\n"
        "А пока можете посмотреть ответы на частые вопросы – напишите /faq\n"
        "Желаем удачного старта! 🚚",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.clear()

@dp.message(CourierForm.phone)
async def process_phone_text(message: types.Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, используйте кнопку '📱 Отправить номер'.",
        reply_markup=phone_kb
    )

# --- Обработчик /faq (добавим для удобства) ---
@dp.message(Command("faq"))
async def faq(message: types.Message):
    text = (
        "❓ *Частые вопросы*\n\n"
        "1️⃣ *Сколько платят?*\n"
        "   Доход от 4 000 ₽ за день + чаевые (100% ваши).\n\n"
        "2️⃣ *Нужна ли своя термосумка?*\n"
        "   Да, обязательна. Можно купить самому или взять у партнёра.\n\n"
        "3️⃣ *Как получить заказы?*\n"
        "   Через приложение курьера – выбираете смены и зону.\n\n"
        "4️⃣ *Что нужно для старта?*\n"
        "   Паспорт, СНИЛС, ИНН, самозанятость (поможем оформить).\n\n"
        "5️⃣ *Можно работать пешком?*\n"
        "   Да, пешком, на вело, самокате, авто.\n\n"
        "По другим вопросам пишите менеджеру – он свяжется с вами."
    )
    await message.answer(text, parse_mode="Markdown")

# --- Настройка webhook ---
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
