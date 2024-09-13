import asyncio

from aiogram.types import Message, CallbackQuery


async def message_alert(message: Message, text: str, deley = 3):
    msg = await message.answer(text)
    await asyncio.sleep(deley)
    await msg.delete()