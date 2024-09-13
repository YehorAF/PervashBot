import asyncio
from datetime import datetime
import uuid

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery,\
    InlineKeyboardMarkup, InlineKeyboardButton

from settings import WEBSITE_URL
from utils.callbacks import MsgToAdminCallback, CancelBtnCallback
from utils.database import db
from utils.formatter import form_cancel_btn
from utils.states import SendComplaintToAdminStates

users_router = Router()


@users_router.message(Command("start"))
async def start(message: Message):
    user_tg_id = message.from_user.id
    _, count = await db.users.get({"user_tg_id": user_tg_id}, {"_id": 1})

    if count < 1:
        await db.users.add_one({
            "user_tg_id": user_tg_id, 
            "status": "user", 
            "saved": [],
            "timestamp": datetime.now()
        })
        
    await message.answer(
        ("Вся інформація про бота знаходитсья за посиланням "
         "https://telegra.ph/Vse-pro-bot-P%D1%96kcha-08-20")
    )


@users_router.message(Command("help"))
async def help(message: Message):
    await message.answer(
        ("Вся інформація про бота знаходитсья за посиланням "
         "https://telegra.ph/Vse-pro-bot-P%D1%96kcha-08-20")
    )


@users_router.message(Command("auth"))
async def auth(message: Message):
    user_tg_id = message.from_user.id
    token = str(uuid.uuid4())

    await db.users.update({"user_tg_id": user_tg_id}, {"token": token})
    await message.answer(
        f"Посилання на сайт {WEBSITE_URL}?token={token}&user_tg_id={user_tg_id}"
    )


@users_router.message(Command("/send_msg_to_admin"))
async def send_msg_to_admin(message: Message, state: FSMContext):
    btns = form_cancel_btn("cancel_sending_message_to_admin")
    await state.set_state(SendComplaintToAdminStates.wait_msg)
    await message.answer(
        "Надшліть повідомлення, у якому описується проблема",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@users_router.message(F.text, SendComplaintToAdminStates.wait_msg)
async def set_text(message: Message, state: FSMContext):
    text = message.text
    await state.update_data({"text": text})

    btns = [[InlineKeyboardButton(
        text="Надіслати",
        callback_data=MsgToAdminCallback(action="send_msg_to_admin").pack()
    )]] + form_cancel_btn("cancel_sending_message_to_admin")

    await message.answer(
        ("Повідомлення було збережено. "
        "Його можна перенаписати, відправивши нове. "
        f"Текст повідомлення:\n\n {text}"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@users_router.callback_query(
    MsgToAdminCallback.filter(F.action == "send_msg_to_admin"),
    SendComplaintToAdminStates.wait_msg
)
async def send_msg(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    text = (await state.get_data())["text"]
    await state.clear()

    await callback.answer()
    await callback.message.answer("Повідомлення було надіслано")

    cur, _ = await db.users.get({"status": {"$in": ["owner", "admin"]}})

    async for admin in cur:
        link = f"https://t.me/{user.username }" if user.username else f"tg://user?id={user.id}"
        try:
            await callback.bot.send_message(
                admin["user_tg_id"],
                ("Було надіслано повідомлення від "
                f"[{user.first_name} {user.last_name or ''}]({link}):\n\n{text}")
            )
        except:
            pass
        finally:
            await asyncio.sleep(1.2)


@users_router.callback_query(
    CancelBtnCallback.filter(F.action == "cancel_sending_message_to_admin"),
    SendComplaintToAdminStates.wait_msg
)
async def cancel_sending_msg(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Дію було відмінено")


# @users_router.inline_query(F.query == "help")
# async def inl_help(inline_query: InlineQuery):
#     btns = form_inline_qury_btns(INLINE_QUERIES_DESCRIPTION)
#     results = [InlineQueryResultArticle(
#         id="help",
#         title="Допомога",
#         description="Допомога з інлайн модом",
#         input_message_content=InputTextMessageContent(
#             message_text=(
#                 "Всі стандіртні команди з отриманням картинок доступні "
#                 "в інлайн моді, але їх потрібно ввести без риски:\n"
#                 "anime_girl - отримати фотографію в стилі японської анімації\n"
#                 "cat - отримати фотографію котика\n"
#                 "monkey - отримати фотогрвфію мавпи\n"
#             )
#         ),
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
#     )]

#     await inline_query.answer(results=results, is_personal=True)