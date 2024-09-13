from datetime import datetime, timedelta
from typing import Any
from redis.asyncio import Redis

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

# from utils.callbacks import ChatSettingsCallback
from utils.database import db
from utils.text import NSFW
from utils.utils import is_admin, is_group


class AdminMessageFilter(Filter):
    def __init__(self) -> None:
        pass


    async def __call__(self, message: Message) -> bool:
        chat = message.chat
        return await is_admin(chat, message.from_user.id) and is_group(chat)
    

# class AdminCallbackFilter(Filter):
#     def __init__(self) -> None:
#         pass


#     async def __call__(
#         self, callback: CallbackQuery
#     ) -> bool:
#         data = callback.data.split(":")
#         callback_data = ChatSettingsCallback(
#             action=data[1], user_id=data[2], chat_id=data[3], selected=data[4])
#         user_id = callback.from_user.id
        
#         return (user_id == callback_data.user_id and 
#                 await is_admin(callback.message.chat, callback.from_user.id))
    

class PhotoFilter(Filter):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis


    async def __call__(self, message: Message) -> bool:
        chat_id = message.chat.id

        if (not is_group(message.chat) or 
            chat_id == message.from_user.id):
            return True

        key = f"group-{chat_id}"
        data = await self._redis.hgetall(key)
        
        # allowed = data[b"allowed"].decode().split("-")
        command = message.text.replace("/", "").replace("@", " ").split()[0]
        show_nsfw = data[b"show_nsfw"].decode()

        # if command not in allowed:
        #     return False

        if show_nsfw == "hide_nsfw" and command in NSFW:
            return False
        
        if not data or data[b"lim"] == b"unlim":
            return True
        
        now = datetime.now()
        time = datetime.strptime(data[b"set_time"].decode(), "%d.%m.%Y-%H:%M:%S")
        reboot = int(data[b"reboot"].decode())

        if now - timedelta(minutes=reboot) > time:
            await self._redis.hmset(key, {
                "set_time": now.strftime("%d.%m.%Y-%H:%M:%S"),
                "count": 1
            })
            return True
        
        count = int(data[b"count"].decode())
        max_count = int(data[b"max"].decode())

        if count < max_count:
            await self._redis.hmset(key, {"count": count + 1})
            return True
        
        return False
    

class BotAdminFilter(Filter):
    def __init__(self, statuses: list[str] = None) -> None:
        self.statuses = statuses or ["owner", "admin"]


    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        
        _, count = await db.users.get({
            "user_tg_id": user_id, "status": {"$in": self.statuses}
        })

        if count < 1:
            return False
        
        return True