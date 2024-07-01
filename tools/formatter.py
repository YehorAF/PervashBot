from aiogram.types import InlineKeyboardButton

from tools.callbacks import PhotoCallback, ChatSettingsCallback


def form_react_btns(
    data: dict[str, str | int],
    pos_key = "pos", 
    neg_key = "neg",
    photo_id_key = "photo_id"
):
    btns = [[
        InlineKeyboardButton(
            text=f"👍{data[pos_key] or ''}",
            callback_data=PhotoCallback(
                action="react", 
                photo_id=str(data[photo_id_key]), 
                reaction="positive"
            ).pack()
        ),
        InlineKeyboardButton(
            text=f"👎{data[neg_key] or ''}",
            callback_data=PhotoCallback(
                action="react", 
                photo_id=str(data[photo_id_key]), 
                reaction="negative"
            ).pack()
        ),
    ]]
    return btns


def form_inline_qury_btns(
    data: dict[str, tuple[str, str]], row_size = 2
) -> list[list[InlineKeyboardButton]]:
    btns = []
    row = []
    i = 0

    for k, v in data.items():
        row.append(InlineKeyboardButton(text=v[0], switch_inline_query=k))
        if (i + 1) % row_size == 0:
            btns.append(row)
            row = []
        i += 1

    if row:
        btns.append(row)

    return btns


def form_chat_settings_btns(
    subs: dict[str, str], chat_id: str | int, user_id: str | int, row_size = 2
) -> list[list[InlineKeyboardButton]]:
    btns = []
    row = []
    i = 0

    for k, v in subs.items():
        row.append(InlineKeyboardButton(
            text=v,
            callback_data=ChatSettingsCallback(
                action=k, user_id=user_id, chat_id=chat_id, selected=False
            ).pack()
        ))
        if (i + 1) % row_size == 0:
            btns.append(row)
            row = []
        i += 1

    if row:
        btns.append(row)

    return btns


def form_selectable_btns(
    data
): 
    pass