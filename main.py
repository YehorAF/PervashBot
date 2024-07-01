import dotenv

dotenv.load_dotenv()

import asyncio
import logging
import sys
import os
from redis.asyncio import Redis

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook

from handlers.admins import admin_router
from handlers.photos import photos_router
from handlers.users import users_router
from handlers.groups import group_router
from tools.database import db, redis
from tools.middlewares import ParamsMiddleware


async def on_shutdown(bot: Bot):
    await bot.session.close()


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format=("%(asctime)s - %(module)s - " 
             "%(levelname)s - %(funcName)s: "
             "%(lineno)d - %(message)s"),
        datefmt="%H:%M:%S",
        stream=sys.stdout
    )

    token = os.getenv("TOKEN")
    # dburl = os.getenv("DBURL")
    # dbname = os.getenv("DBNAME")
    # db = Database(dburl, dbname)
    storage = RedisStorage(Redis())

    dp = Dispatcher(storage=storage)
    dp.message.middleware(ParamsMiddleware(db, redis))
    dp.callback_query.middleware(ParamsMiddleware(db, redis))
    dp.inline_query.middleware(ParamsMiddleware(db, redis))
    dp.include_router(admin_router)
    dp.include_router(users_router)
    dp.include_router(photos_router)
    dp.include_router(group_router)
    dp.shutdown.register(on_shutdown)

    bot = Bot(token=token, parse_mode=ParseMode.HTML)
    
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())