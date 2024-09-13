from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.callbacks import CancelBtnCallback, AddPostCallback

cancel_adding_post_btn = InlineKeyboardButton(
    text="Відмінити", callback_data=CancelBtnCallback(
        action="cancel_add_post").pack())
cancel_adding_post_ikm = InlineKeyboardMarkup(
    inline_keyboard=[[cancel_adding_post_btn]])

show_tags_btn = InlineKeyboardButton(
    text="Показати таги", callback_data=AddPostCallback(
        action="show_tags", from_action="check_post").pack())
show_tags_ikm = InlineKeyboardMarkup(inline_keyboard=[[show_tags_btn]])