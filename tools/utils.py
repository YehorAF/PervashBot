from aiogram.enums import ChatMemberStatus
from aiogram.types import Chat


async def is_admin(chat: Chat, user_id: str | int) -> bool | None:
    user = await chat.get_member(user_id)

    if user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        return True
    

def is_group(chat: Chat) -> bool | None:
    if chat.type in ['group', 'supergroup']:
        return True