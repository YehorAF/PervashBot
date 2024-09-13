from redis.asyncio import Redis

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from typing import Union, Callable, Awaitable, Any
import logging

from tools.database import Database


class ParamsMiddleware(BaseMiddleware):
    def __init__(self, db: Database, redis: Redis) -> None:
        self._db: Database = db
        self._redis: Redis = redis


    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: dict[str, Any] 
    ):
        data |= {"db": self._db, "redis": self._redis}

        try:
            return await handler(event, data)
        except Exception as ex_:
            logging.error(f" error in handler: {ex_}")