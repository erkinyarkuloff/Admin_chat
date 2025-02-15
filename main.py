import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from asyncio import sleep

# Tokin va admin ID
API_TOKEN = "7881605660:AAFJI5MG1Yyb0s3LFR-mUyUgUNADn4Vglig"
ADMIN_ID = 7888045216  # O'zingizning Telegram ID'ingizni yozing

# Logger sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Foydalanuvchi holati uchun State
class ChatState(StatesGroup):
    language = State()
    waiting_for_message = State()

# Til menyusi
language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
language_keyboard.add(KeyboardButton("🇺🇿 O‘zbek"), KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English"))

# Start buyrug'i
@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    text = ("Assalom Aleykum!\n"
            "🧑‍💻Siz anketa kanal admini bilan aloqa botidasiz.\n"
            "Marhamat, pastdagi menulardan muloqot tilini tanlang:")

    text_ru = ("Здравствуйте!\n"
               "🧑‍💻Вы находитесь в боте связи с администратором канала анкет.\n"
               "Пожалуйста, выберите язык общения из меню ниже:")

    text_en = ("Hello!\n"
               "🧑‍💻You are in the questionnaire channel admin contact bot.\n"
               "Please select a communication language from the menu below:")

    await message.answer(f"{text}\n\n{text_ru}\n\n{text_en}", reply_markup=language_keyboard)
    await ChatState.language.set()

# Tilni noto‘g‘ri tanlash
@dp.message_handler(lambda message: message.text not in ["🇺🇿 O‘zbek", "🇷🇺 Русский", "🇬🇧 English"], state=ChatState.language)
async def invalid_language(message: types.Message):
    await message.answer("Iltimos, muloqot qiladigan tilingizni menudan tanlang:", reply_markup=language_keyboard)

# Til tanlaganda
@dp.message_handler(lambda message: message.text in ["🇺🇿 O‘zbek", "🇷🇺 Русский", "🇬🇧 English"], state=ChatState.language)
async def choose_language(message: types.Message, state: FSMContext):
    user_language = message.text
    await state.update_data(language=user_language)

    if user_language == "🇺🇿 O‘zbek":
        text = "Marhamat, kanal yoki anketalar bo‘yicha savol va taklifingizni yozishingiz mumkin:"
    elif user_language == "🇷🇺 Русский":
        text = "Пожалуйста, напишите ваш вопрос или предложение по каналу и анкетам:"
    else:
        text = "Please write your question or suggestion about the channel and questionnaires:"

    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await ChatState.waiting_for_message.set()

    # Faqat foydalanuvchi 10 daqiqa ichida yozmasa, bot qayta boshlaydi
    async def reset_if_no_message():
        await sleep(600)
        current_state = await state.get_state()
        if current_state == ChatState.waiting_for_message.state:
            await start(message, state)

    dp.loop.create_task(reset_if_no_message())

# Foydalanuvchi xabar yuborsa, adminga yetkazish
@dp.message_handler(content_types=types.ContentTypes.ANY, state=ChatState.waiting_for_message)
async def send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"[Profilga o‘tish](tg://user?id={user_id})"

    # "Javob berish" tugmasi
    reply_button = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✍️ Javob berish", callback_data=f"reply_{message.message_id}_{user_id}")
    )

    caption = f"📩 *Yangi xabar:*\n\n{message.text or '📎 Media fayl'}\n\n👤 {username} ({user_id})"

    if message.text:
        msg = await bot.send_message(ADMIN_ID, caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.photo:
        msg = await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.video:
        msg = await bot.send_video(ADMIN_ID, message.video.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.voice:
        msg = await bot.send_voice(ADMIN_ID, message.voice.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.document:
        msg = await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)

    # Xabarni xotirada saqlash
    await state.update_data({f"msg_{msg.message_id}": message.message_id})

# Admin "Javob berish" tugmasini bossa
@dp.callback_query_handler(lambda call: call.data.startswith("reply_"))
async def reply_to_user(call: types.CallbackQuery, state: FSMContext):
    _, msg_id, user_id = call.data.split("_")
    await state.update_data(replying_to=(msg_id, user_id))
    await call.message.answer("✍️ Javobingizni yozing:")
    await call.answer()

# Admin javob yozganda
@dp.message_handler(content_types=types.ContentTypes.ANY, user_id=ADMIN_ID)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reply_info = data.get("replying_to")

    if reply_info:
        msg_id, user_id = reply_info

        if message.text:
            await bot.send_message(user_id, f"👨‍💻 *Admin javobi:*\n\n{message.text}", parse_mode="Markdown", reply_to_message_id=int(msg_id))
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption="👨‍💻 *Admin javobi*", parse_mode="Markdown", reply_to_message_id=int(msg_id))
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption="👨‍💻 *Admin javobi*", parse_mode="Markdown", reply_to_message_id=int(msg_id))
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id, caption="👨‍💻 *Admin javobi*", parse_mode="Markdown", reply_to_message_id=int(msg_id))
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption="👨‍💻 *Admin javobi*", parse_mode="Markdown", reply_to_message_id=int(msg_id))

        await state.update_data(replying_to=None)
    else:
        await message.answer("❌ Javob berish uchun xabar tanlanmadi!")

# Botni ishga tushirish
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)