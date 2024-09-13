from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from utils.callbacks import AddPostCallback, PostReactCallback,\
    PostMoveCallback, ReactionEnum, MovementEnum, ComplaintOnPostCallback,\
    CancelBtnCallback, PostManageCallback


def form_cancel_btn(action: str):
    return [[InlineKeyboardButton(
        text="Відмінити",
        callback_data=CancelBtnCallback(action=action).pack()
    )]]


def form_check_post_btns(
    is_hidden: bool, is_nsfw: bool, from_action: str
):
    change_media_btn = InlineKeyboardButton(
        text="Поміняти медіа", 
        callback_data=AddPostCallback(
            action="update_post", from_action=from_action).pack()
    )
    change_description_btn = InlineKeyboardButton(
        text="Поміняти опис", 
        callback_data=AddPostCallback(
            action="update_description", from_action=from_action).pack()
    )
    cahnge_tags_btn = InlineKeyboardButton(
        text="Поміняти таги", 
        callback_data=AddPostCallback(
            action="update_tags", from_action=from_action).pack()
    )
    is_hidden_btn = InlineKeyboardButton(
        text=f"Не показувати автора: {'✅' if is_hidden else '❌'}", 
        callback_data=AddPostCallback(
            action="is_hidden", 
            from_action=from_action, 
            data=is_hidden
        ).pack()
    )
    is_nsfw_btn = InlineKeyboardButton(
        text=f"Дорослий контент: {'✅' if is_nsfw else '❌'}", 
        callback_data=AddPostCallback(
            action="is_nsfw", 
            from_action=from_action, 
            data=is_nsfw
        ).pack()
    )
    set_post_btn = InlineKeyboardButton(
        text="Завантажити пост",
        callback_data=AddPostCallback(
            action="set_post", 
            from_action=from_action
        ).pack()
    )

    return [
        [change_media_btn],
        [change_description_btn],
        [cahnge_tags_btn],
        [is_hidden_btn],
        [is_nsfw_btn],
        [set_post_btn]
    ]


def form_tag_viewer_btns():
    return InlineKeyboardButton(
    text="Показати таги", callback_data=AddPostCallback(
        action="show_tags", 
        from_action="check_post",
    ).pack())


def form_post_previewer(message: Message, data: dict):
    file_id = data["file_id"]
    file_type = data["file_type"]
    description = data["description"]
    btn = form_tag_viewer_btns()
    func = {
        "animation": message.answer_animation, 
        "photo": message.answer_photo,
        "video": message.answer_video
    }[file_type]
    msg_args = [file_id]
    msg_kwargs = {
        "caption": description, 
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=[[btn]])
    }

    return func, msg_args, msg_kwargs


def form_post_adding_move_btns(
    back_action: str = None,
    next_action: str = None,
    from_action: str = None
):
    btns = []

    if back_action:
        btns.append(InlineKeyboardButton(
            text="Повернутись", 
            callback_data=AddPostCallback(
                action=back_action, from_action=from_action).pack()
        ))

    if next_action:
        btns.append(InlineKeyboardButton(
            text="Далі", 
            callback_data=AddPostCallback(
                action=next_action, from_action=from_action).pack()
        ))

    return [btns]


def form_reaction_btns(
    post_id: str, 
    pos_reacts: int,
    neg_reacts: int,
    request_id: str = None, 
    command: str = None, 
    offset: int = None,
    is_max: bool = False
):
    btns = []

    positive_btn = InlineKeyboardButton(
        text=f"👍 {pos_reacts if pos_reacts else ''}",
        callback_data=PostReactCallback(
            post_id=post_id, 
            request_id=request_id, 
            reaction=ReactionEnum.positive
        ).pack()
    )
    negative_btn = InlineKeyboardButton(
        text=f"👎 {neg_reacts if neg_reacts else ''}",
        callback_data=PostReactCallback(
            post_id=post_id,
            request_id=request_id, 
            reaction=ReactionEnum.negative
        ).pack()
    )
    btns.append([positive_btn, negative_btn])

    save_btn = InlineKeyboardButton(
        text=f"⭐️ Зберегти",
        callback_data=PostReactCallback(
            post_id=post_id, reaction=ReactionEnum.save
        ).pack()
    )
    btns.append([save_btn])

    complaint_btn = InlineKeyboardButton(
        text=f"❗️Поскаржитись",
        callback_data=PostReactCallback(
            post_id=post_id, reaction=ReactionEnum.complaint
        ).pack()
    )
    btns.append([complaint_btn])

    if request_id:
        move_btns = []
        if not offset:
            prev_btn = InlineKeyboardButton(
                text="⬅️",
                callback_data=PostMoveCallback(
                    move=MovementEnum.back,
                    request_id=request_id, 
                    command=command, 
                    offset=offset
                ).pack()
            )
            move_btns.append(prev_btn)

        if not is_max:
            next_btn = InlineKeyboardButton(
                text="➡️",
                callback_data=PostMoveCallback(
                    move=MovementEnum.forward,
                    request_id=request_id, 
                    command=command, 
                    offset=offset
                ).pack()
            )
            move_btns.append(next_btn)

        btns.append(move_btns)

    return btns


def form_manage_post_btns(
    post_id: str, 
    user_tg_id: int = 0, 
    is_admin = False, 
    hiddened_by: str = None
):
    delete_btn = InlineKeyboardButton(
        text="Видалити", 
        callback_data=PostManageCallback(
            action="delete_post", post_id=post_id, user_tg_id=user_tg_id
        ).pack()
    )

    btns = []
    if not is_admin:
        btns.append([delete_btn])
    else:
        ban_user_btn = InlineKeyboardButton(
            text="Заблокувати",
            callback_data=PostManageCallback(
                action="ban_user", post_id=post_id, user_tg_id=user_tg_id
            ).pack()
        )
        btns.append([delete_btn, ban_user_btn])

    if hiddened_by == "hidden_by_user" and not is_admin:
        hide_btn = InlineKeyboardButton(
            text="Відкрити",
            callback_data=PostManageCallback(
                action="opened_by_user", 
                post_id=post_id, 
                user_tg_id=user_tg_id
            ).pack()
        )
    elif hiddened_by == "hidden_by_admin" and is_admin:
        hide_btn = InlineKeyboardButton(
            text="Відкрити",
            callback_data=PostManageCallback(
                action="opened_by_admin", 
                post_id=post_id, 
                user_tg_id=user_tg_id
            ).pack()
        )
    else:
        hide_btn = InlineKeyboardButton(
            text="Відкрити",
            callback_data=PostManageCallback(
                action="hidden_by_admin" if is_admin else "hidden_by_user", 
                post_id=post_id, 
                user_tg_id=user_tg_id
            ).pack()
        )

    btns.append([hide_btn])

    return btns


def form_complaint_btns(post_id: str):
    send_complaint_btn = InlineKeyboardButton(
        text="Надіслати",
        callback_data=ComplaintOnPostCallback(
            action="complaint", 
            post_id=post_id, 
            user_tg_id=0
        ).pack()
    )

    return [[send_complaint_btn]] + form_cancel_btn("cancel_complaint")


def form_reaction_on_complaint_btns(
    post_id: str, user_tg_id: str | int
):
    delete_post_btn = InlineKeyboardButton(
        text="Видалити пост",
        callback_data=ComplaintOnPostCallback(
            action="delete_post", post_id=post_id, user_tg_id=user_tg_id
        ).pack()
    )
    reject_complaint_btn = InlineKeyboardButton(
        text="Відхилити скаргу",
        callback_data=ComplaintOnPostCallback(
            action="reject_complaint", post_id=post_id, user_tg_id=user_tg_id
        ).pack()
    )
    show_post_btn = InlineKeyboardButton(
        text="Переглянути пост",
        callback_data=ComplaintOnPostCallback(
            action="show_post", post_id=post_id, user_tg_id=user_tg_id
        ).pack()
    )
    return [[delete_post_btn, reject_complaint_btn], [show_post_btn]]


def form_action_on_complaint_btns(data: dict):
    action = data["action"]

    if action == "delete_post":
        btn = InlineKeyboardButton(
            text="Видалити пост",
            callback_data=ComplaintOnPostCallback(
                action=action + "_act", 
                post_id=data["post_id"],
                user_tg_id=data["user_tg_id"]
            ).pack()
        )
    else:
        btn = InlineKeyboardButton(
            text="Відхилити скаргу",
            callback_data=ComplaintOnPostCallback(
                action=action + "_act", 
                post_id=data["post_id"],
                user_tg_id=data["user_tg_id"]
            ).pack()
        )

    return [[btn]]