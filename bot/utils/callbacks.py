from aiogram.filters.callback_data import CallbackData

from enum import Enum
from typing import Any, Optional


class ReactionEnum(str, Enum):
    positive: str = "positive"
    negative: str = "negative"
    save: str = "save"
    complaint: str = "complaint"


class MovementEnum(str, Enum):
    back: str = "back"
    forward: str = "forward"


class PostReactCallback(CallbackData, prefix="pc"):
    post_id: str
    request_id: str | None = None
    reaction: ReactionEnum


class PostManageCallback(CallbackData, prefix="pmc"):
    action: str
    post_id: str
    user_tg_id: int


class PostMoveCallback(CallbackData, prefix="pm"):
    move: MovementEnum
    request_id: str
    command: str
    offset: int


class AddPostCallback(CallbackData, prefix="apc"):
    action: str
    from_action: str
    data: bool | None = None


class ComplaintOnPostCallback(CallbackData, prefix="cop"):
    action: str
    post_id: str
    user_tg_id: Optional[int]


class MsgToAdminCallback(CallbackData, prefix="mta"):
    action: str


class CancelBtnCallback(CallbackData, prefix="cbc"):
    action: str