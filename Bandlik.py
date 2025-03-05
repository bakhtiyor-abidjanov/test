import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand, ReplyKeyboardRemove

TOKEN = "7567705481:AAF1CDhm53n6xrSl_3sjDzK-881uELw8chs"
ADMIN_ID = (5126280072, 302792056,)

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            goal TEXT,
            contact TEXT
        )
        """)
        await db.commit()

class Form(StatesGroup):
    full_name = State()
    goal = State()
    contact = State()

class NewGoal(StatesGroup):
    goal = State()

contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Kontakt yuborish", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Меню")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await message.answer("👋 Assalomu aleykum! Botimizga xush kelibsiz!\n\nIltimos, ismingizni kiriting:")
    await state.set_state(Form.full_name)

@dp.message(Form.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📌 Masalangiz mazmunini kiriting:")
    await state.set_state(Form.goal)

@dp.message(Form.goal)
async def process_goal(message: types.Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await message.answer("📱 Aloqaga chiqishimiz uchun kontaktingizni yuboring:", reply_markup=contact_keyboard)
    await state.set_state(Form.contact)

@dp.message(Form.contact)
async def process_contact(message: types.Message, state: FSMContext):
    if not message.contact:
        await message.answer("❗ Iltimos, biz bilan bog‘lanish uchun kontaktingizni yuboring.")
        return
    
    data = await state.get_data()
    full_name = data["full_name"]
    goal = data["goal"]
    contact = message.contact.phone_number
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT INTO users (full_name, goal, contact) VALUES (?, ?, ?)", (full_name, goal, contact))
        await db.commit()
    
    await message.answer("✅ Murojaatingiz qabul qilindi! Call-markaz operatorlari tez orada siz bilan bog‘lanishadi.", reply_markup=ReplyKeyboardRemove())
    await message.answer("☎️ Agar sizga hali ham bog‘lanishmagan bo‘lsa, /qayta_sorov buyrug‘ini bosing.")
    await state.clear()

@dp.message(Command("DB"))
async def get_data(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("🚫 Sizda bu buyruqni ishlatish uchun ruxsat yo‘q.")
        return

    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT * FROM users") as cursor:
            user_data = await cursor.fetchall()

    if not user_data:
        await message.answer("📂 Ma‘lumotlar bazasi bo‘sh.")
        return

    response = "📋 Foydalanuvchilar ro‘yxati:\n\n"
    for user in user_data:
        response += f"🆔 ID: {user[0]}\n👤 F.I.Sh: {user[1]}\n📌 Masala: {user[2]}\n📞 Telefon: {user[3]}\n---\n"

    for part in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await message.answer(part)

@dp.message(Command("clear_db"))
async def clear_database(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("🚫 Sizda bu buyruqni ishlatish uchun ruxsat yo‘q.")
        return

    async with aiosqlite.connect("users.db") as db:
        await db.execute("DELETE FROM users")
        await db.execute("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'users'")  # Сброс ID
        await db.commit()

    await message.answer("✅ Ma'lumotlar bazasi tozalandi, ID qayta boshlandi.")


@dp.message(Command("delete_user"))
async def delete_user(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("🚫 Sizda bu buyruqni ishlatish uchun ruxsat yo‘q.")
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❗ Iltimos, foydalanuvchi ID sini to‘g‘ri formatda kiriting.\nMisol: `/delete_user 3`")
        return

    user_id = int(args[1])

    async with aiosqlite.connect("users.db") as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()

        async with db.execute("SELECT id FROM users ORDER BY id") as cursor:
            users = await cursor.fetchall()

        for new_id, (old_id,) in enumerate(users, start=1):
            await db.execute("UPDATE users SET id = ? WHERE id = ?", (new_id, old_id))

        await db.commit()

    await message.answer(f"✅ Foydalanuvchi ID-{user_id} o'chirildi. ID yangilandi.")



@dp.message(Command("admin_buyruqlari"))
async def show_menu(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("🚫 Sizda bu buyruqni ishlatish uchun ruxsat yo‘q.")
        return
    await message.answer("/DB - Barcha murojaatlarni ko'rish uchun\n/delete_user - bitta murojaatni o'chirib yuborish uchun\n/clear_db - Barcha murojatlarni o'chirib yuborish uchun")

@dp.message(Command("yangi_murojaat"))
async def new_goal(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT full_name, contact FROM users WHERE contact = (SELECT contact FROM users WHERE full_name = (SELECT full_name FROM users WHERE contact IS NOT NULL ORDER BY id DESC LIMIT 1))") as cursor:
            user_data = await cursor.fetchone()

    if not user_data:
        await message.answer("❗ Iltimos, avval /start orqali ro‘yxatdan o‘ting.")
        return

    full_name, contact = user_data

    await state.update_data(full_name=full_name, contact=contact)

    await message.answer("📌 Yangi masalangiz mazmunini kiriting:")
    await state.set_state(NewGoal.goal)

@dp.message(NewGoal.goal)
async def process_new_goal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = data["full_name"]
    contact = data["contact"]
    goal = message.text

    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT INTO users (full_name, goal, contact) VALUES (?, ?, ?)", (full_name, goal, contact))
        await db.commit()

    await message.answer("✅ Yangi masalangiz qabul qilindi! Call-markaz operatorlari tez orada siz bilan bog‘lanishadi.")
    await state.clear()

@dp.message(Command("my_id"))
async def send_my_id(message: types.Message):
    await message.answer(f"🆔 Sizning Telegram ID yingiz: {message.from_user.id}")

@dp.message(Command('qayta_sorov'))
async def get_user_id(message: types.Message):
    await message.answer("🙏 Rahmat, sizga tez orada bog‘lanishadi.")

async def set_commands():
    commands = [
        BotCommand(command='qayta_sorov', description="Sizga bog'lanishmadimi?"),
        BotCommand(command='yangi_murojaat', description='Boshqa murojaatingiz bormi?'),
        BotCommand(command='admin_buyruqlari', description="Adminning buyruqlarini ko'rish"),
        BotCommand(command='my_id', description="Telegram ID yingizni ko'rish uchun")
    ]
    await bot.set_my_commands(commands)

async def main():
    await init_db()
    await set_commands()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

