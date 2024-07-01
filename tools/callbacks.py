from aiogram.filters.callback_data import CallbackData

from enum import Enum


class ReactionEnum(str, Enum):
    positive: str = "positive"
    negative: str = "negative"


class PhotoCallback(CallbackData, prefix="pc"):
    action: str
    photo_id: str
    reaction: ReactionEnum


class ChatSettingsCallback(CallbackData, prefix="csc"):
    action: str
    user_id: int
    chat_id: int
    selected: bool | None