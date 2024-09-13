import asyncio
import logging
import sys
from redis.asyncio import Redis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook

from settings import TOKEN
from handlers.add_posts import add_posts_router
from handlers.use_posts import use_posts_router
from handlers.complaint import complaint_router
from handlers.users import users_router
from handlers.admins import admin_router
from handlers.manage_posts import manage_posts_router

async def on_shutdown(bot: Bot):
    await bot.session.close()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s - %(module)s - " 
             "%(levelname)s - %(funcName)s: "
             "%(lineno)d - %(message)s"),
        datefmt="%H:%M:%S",
        stream=sys.stdout
    )

    storage = RedisStorage(Redis())

    dp = Dispatcher(storage=storage)
    dp.include_router(add_posts_router)
    dp.include_router(use_posts_router)
    dp.include_router(complaint_router)
    dp.include_router(users_router)
    dp.include_router(admin_router)
    dp.include_router(manage_posts_router)
    dp.shutdown.register(on_shutdown)

    bot = Bot(token=TOKEN)
    
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())