import asyncio
import io
import logging
import pandas as pd

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from tools.database import Database
from tools.filters import BotAdminFilter


admin_router = Router()


@admin_router.message(Command(commands=["send_message"]), BotAdminFilter())
async def send_message(message: Message, db: Database):
    msg = message.reply_to_message
    users, _ = await db.users.get({})

    async for user in users:
        try:
            await msg.send_copy(user["tg_id"])
        except Exception as ex_:
            logging.info(f"cannot send message to {user['tg_id']}: {ex_}")
        await asyncio.sleep(1.2)

    groups, _ = await db.groups.get({})

    async for group in groups:
        try:
            await msg.send_copy(group["chat_tg_id"])
        except Exception as ex_:
            logging.info(f"cannot send message to {group['chat_tg_id']}: {ex_}")
        await asyncio.sleep(1.2)


@admin_router.message(Command(commands=["get_users"]), BotAdminFilter())
async def get_users(message: Message, db: Database):
    users = []
    cur, count = await db.users.get({}, {"_id": 0})

    async for user in cur:
        users.append(user)

    buf = io.BytesIO()
    df = pd.DataFrame(users)
    df.to_csv(buf)
    buf.seek(0)

    await message.reply_document(BufferedInputFile(buf.read(), "users.csv"))