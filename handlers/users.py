from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineQuery,\
    InlineKeyboardMarkup, InlineKeyboardButton,\
    InlineQueryResultArticle, InputTextMessageContent

from tools.database import Database
from tools.formatter import form_inline_qury_btns
from tools.text import INLINE_QUERIES_DESCRIPTION


users_router = Router()


@users_router.message(Command("start"))
async def start(message: Message, db: Database):
    user_tg_id = message.from_user.id
    _, count = await db.users.get({"tg_id": user_tg_id}, {"_id": 1})

    if count < 1:
        dt = datetime.now().strftime("%d.%m.%Y-%H:%M:%S")
        await db.users.add_one(
            {"tg_id": user_tg_id, "status": "user", "signed": dt})
        
    await message.answer(
        ("Привіт, шановний друже! Це тестовий бот зі всякою фігньою, "
         "який має обширну базу різних пікч.\n\n"
        "Зараз маєш доступ до наступних команд:\n"
        "/start - запустити бота\n"
        "/help - команда для допомоги\n"
        "/anime_girl - отримати фотографію в стилі японської анімації\n"
        "/cat - отримати фотографію котика\n"
        "/monkey - отримати фотогрвфію мавпи\n")
    )


@users_router.message(Command("help"))
async def help(message: Message):
    await message.answer(
        ("Список всіх команд:\n"
        "/start - запустити бота\n"
        "/help - команда для допомоги\n"
        "/anime_girl - отримати фотографію в стилі японської анімації\n"
        "/cat - отримати фотографію котика\n")
    )


@users_router.inline_query(F.query == "help")
async def inl_help(inline_query: InlineQuery):
    btns = form_inline_qury_btns(INLINE_QUERIES_DESCRIPTION)
    results = [InlineQueryResultArticle(
        id="help",
        title="Допомога",
        description="Допомога з інлайн модом",
        input_message_content=InputTextMessageContent(
            message_text=(
                "Всі стандіртні команди з отриманням картинок доступні "
                "в інлайн моді, але їх потрібно ввести без риски:\n"
                "anime_girl - отримати фотографію в стилі японської анімації\n"
                "cat - отримати фотографію котика\n"
                "monkey - отримати фотогрвфію мавпи\n"
            )
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )]

    await inline_query.answer(results=results, is_personal=True)