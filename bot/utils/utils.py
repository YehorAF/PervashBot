from aiogram.enums import ChatMemberStatus
from aiogram.types import Chat, Message


async def is_admin(chat: Chat, user_id: str | int) -> bool | None:
    user = await chat.get_member(user_id)

    if user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        return True
    

def is_group(chat: Chat) -> bool | None:
    if chat.type in ['group', 'supergroup']:
        return True
    

def get_file_id(message: Message):
    if message.photo:
        return message.photo[-1].file_id, "photo"
    elif message.animation:
        return message.animation.file_id, "animation"
    elif message.video:
        return message.video.file_id, "video"
    else:
        raise ValueError("Cannot define media type and get file id")