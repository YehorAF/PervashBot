from aiogram import Bot


async def get_chat(user: str | int, bot: Bot):
    chat = await bot.get_chat(user)

    if not chat:
        raise ValueError(f"Cannot get user: {user}")

    return chat