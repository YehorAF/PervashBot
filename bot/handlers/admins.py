import asyncio
import io
import logging
import pandas as pd

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ParseMode

from handler_operations.users import get_chat
from utils.database import db
from utils.filters import BotAdminFilter

admin_router = Router()


@admin_router.message(Command(commands=["send_message"]), BotAdminFilter())
async def send_message(message: Message):
    msg = message.reply_to_message
    users, _ = await db.users.get({})

    async for user in users:
        try:
            await msg.send_copy(user["user_tg_id"])
        except Exception as ex_:
            logging.info(f"cannot send message to {user['tg_id']}: {ex_}")
        await asyncio.sleep(1.2)


@admin_router.message(Command(commands=["get_users"]), BotAdminFilter())
async def get_users(message: Message):
    users = []
    cur, count = await db.users.get({}, {"_id": 0})

    async for user in cur:
        users.append(user)

    buf = io.BytesIO()
    df = pd.DataFrame(users)
    df.to_csv(buf)
    buf.seek(0)

    await message.reply_document(BufferedInputFile(buf.read(), "users.csv"))


@admin_router.message(Command(commands=["unban_user"]), BotAdminFilter())
async def unban_user(message: Message):
    try:
        data = message.text.split()
        user = await get_chat(data[1], message.bot)
        user_tg_id = user.id
    except Exception as ex_:
        logging.info(ex_) 
        return

    result = await db.users.update(
        {"user_tg_id": user_tg_id}, {"status": "user"})
    
    if result.modified_count < 1:
        await message.answer("Не вдалось розблукувати користувача")
        return

    await db.posts.update({"user_tg_id": user_tg_id}, {"status": "opened"})    
    await message.answer(
        f"Користувач був розблокований [{user_tg_id}](tg://user?id={user_tg_id})"
    )


@admin_router.message(Command(commands=["get_user"]), BotAdminFilter())
async def show_user_info(message: Message):
    try:
        data = message.text.split()
        user = await get_chat(data[1], message.bot)
        user_tg_id = user.id
    except Exception as ex_:
        logging.info(ex_) 
        return
    
    text = ""
    try:
        text += f"Користувач [{user.first_name} {user.last_name or ''}](tg://user?id={user_tg_id})\n"
        text += f"Юзернейм: {user.username or '-'}\n"
    except:
        pass
    text += f"Айді користувача: {user_tg_id}\n"
    
    user = await db.users.r.find_one({"user_tg_id": user_tg_id})
    text += f"Статус: {user['status']}"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@admin_router.message(Command(commands=["set_admin"]), BotAdminFilter(["owner"]))
async def set_admin(message: Message):
    try:
        data = message.text.split()
        user = await get_chat(data[1], message.bot)
        user_tg_id = user.id
    except Exception as ex_:
        logging.info(ex_) 
        return
    
    result = await db.users.update(
        {"user_tg_id": user_tg_id}, {"status": "admin"}
    )

    if result.modified_count < 1:
        await message.answer(
            "Не вдалось призначити адміністратора (не є в БД)"
        )
    else:
        await message.answer((
            "Було призначено нового адміністратора: "
            f"[{user.first_name} {user.last_name or ''}]"
            f"(tg://user?id={user_tg_id})"
        ))