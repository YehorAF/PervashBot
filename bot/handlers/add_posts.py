from datetime import datetime
import logging

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from handler_operations.adding_post import add_media_to_storage,\
    add_description_to_storage, add_tags_to_storage
from handler_operations.using_post import make_results_for_message
from utils.callbacks import AddPostCallback, CancelBtnCallback
from utils.database import db
from utils.formatter import form_check_post_btns,\
    form_post_previewer, form_post_adding_move_btns
from utils.keyboard import cancel_adding_post_ikm, cancel_adding_post_btn
from utils.notifiers import message_alert
from utils.states import AddingPostStates
from utils.utils import get_file_id

add_posts_router = Router(name="add_posts_router")


# start adding pictures
@add_posts_router.message(Command("add_post"))
async def start_adding_post(message: Message, state: FSMContext):
    user_tg_id = message.from_user.id
    result = await db.users.r.find_one(
        {"user_tg_id": user_tg_id, "status": {"$ne": "blocked"}}
    )

    if not result:
        await message.answer("Вам заборонено додавати пости!")
    else:
        await state.set_state(AddingPostStates.add_post)
        await message.answer(
            text="Надішліть одну картинки чи гіфку", 
            reply_markup=cancel_adding_post_ikm
        )


@add_posts_router.callback_query(
    AddingPostStates.add_description, 
    AddPostCallback.filter(F.action == "reset_media")
)
async def reset_media(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddingPostStates.add_post)
    await callback.message.answer(
        text="Надішліть одну картинки чи гіфку", 
        reply_markup=cancel_adding_post_ikm
    )


@add_posts_router.message(AddingPostStates.add_post)
async def add_post(message: Message, state: FSMContext):
    try:
        await add_media_to_storage(message, state)
    except (ValueError, TypeError) as ex_:
        logging.info(ex_)
    else:
        btns = form_post_adding_move_btns(
            "reset_media", "skip", "add_description") + [[cancel_adding_post_btn]]
        await state.set_state(AddingPostStates.add_description)
        await message.answer(
            text="Надішліть тепер підпис до посту (не більше 2000 символів)", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )


@add_posts_router.callback_query(
    AddingPostStates.add_tags,
    AddPostCallback.filter(F.action == "reset_description")
)
async def reset_description(callback: CallbackQuery, state: FSMContext):
    btns = form_post_adding_move_btns(
        "reset_media", "skip", "add_description") + [[cancel_adding_post_btn]]
    await state.set_state(AddingPostStates.add_description)
    await callback.message.answer(
        text="Надішліть тепер підпис до посту (не більше 2000 символів)", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@add_posts_router.callback_query(
    AddingPostStates.add_description,
    AddPostCallback.filter(F.action == "skip")
)
async def skip_adding_description(callback: CallbackQuery, state: FSMContext):
    btns = form_post_adding_move_btns(
        "reset_description", from_action="skip") + [[cancel_adding_post_btn]]
    await state.update_data({"description": ""})
    await state.set_state(AddingPostStates.add_tags)
    await callback.message.answer(
        text=("Тепер можете додати таги, за "
              "якими будуть шукати фотографії. "
              "Вони повинні починатись з '#', а пробіли позначатись '_'. "
              "Бажано, щоб у кожному тегу було максимум 2-3 слова, які "
              "описують фотографію\n\n"
              "Приклад: #природа #ліс #сіра_миш #зелений_дуб "
              "#вставити_ще_щось_подібне"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )    


@add_posts_router.message(AddingPostStates.add_description, F.text)
async def add_description(message: Message, state: FSMContext):
    try:
        await add_description_to_storage(message, state)
    except ValueError as ex_:
        logging.info(ex_)
    else:
        btns = form_post_adding_move_btns(
            "reset_description", from_action="add_description"
        ) + [[cancel_adding_post_btn]]
        await state.set_state(AddingPostStates.add_tags)
        await message.answer(
            text=("Тепер можете додати таги, за "
                  "якими будуть шукати фотографії. "
                  "Вони повинні починатись з '#', а пробіли позначатись '_'. "
                  "Бажано, щоб у кожному тегу було максимум 2-3 слова, які "
                  "описують фотографію\n\n"
                  "Приклад: #природа #ліс #сіра_миш #зелений_дуб "
                  "#вставити_ще_щось_подібне"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )


@add_posts_router.message(AddingPostStates.add_tags)
async def add_tags_and_updating(message: Message, state: FSMContext):
    await add_tags_to_storage(message, state)

    data = await state.get_data()
    func, msg_args, msg_kwargs = form_post_previewer(message, data)
    await state.set_state(AddingPostStates.check)
    await func(*msg_args, **msg_kwargs)

    is_hidden = False
    is_nsfw = False
    btns = form_check_post_btns(
        is_hidden, is_nsfw, "check_post_info") + [[cancel_adding_post_btn]]
    await message.answer(
        text="Чи все добре?", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@add_posts_router.message(AddingPostStates.update)
async def update_post(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")

    try:
        await {
            "update_tags": add_tags_to_storage,
            "update_post": add_media_to_storage,
            "update_description":add_description_to_storage
        }.get(action)(message, state)
    except (ValueError, TypeError) as ex_:
        logging.info(ex_)
        return

    data = await state.get_data()
    func, msg_args, msg_kwargs = form_post_previewer(message, data)
    await state.set_state(AddingPostStates.check)
    await func(*msg_args, **msg_kwargs)

    is_hidden = data.get("is_hidden")
    is_nsfw = data.get("is_nsfw")
    btns = form_check_post_btns(
        is_hidden, is_nsfw, "check_post_info") + [[cancel_adding_post_btn]]
    await message.answer(
        text="Чи все добре?", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@add_posts_router.callback_query(
    AddPostCallback.filter(F.action == "cancel_updating")
)
async def cancel_updating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    func, msg_args, msg_kwargs = form_post_previewer(callback.message, data)
    await state.set_state(AddingPostStates.check)
    await func(*msg_args, **msg_kwargs)

    is_hidden = data.get("is_hidden")
    is_nsfw = data.get("is_nsfw")
    btns = form_check_post_btns(
        is_hidden, is_nsfw, "check_post_info") + [[cancel_adding_post_btn]]
    await callback.message.answer(
        text="Чи все добре?", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@add_posts_router.callback_query(
    AddingPostStates.check,
    AddPostCallback.filter(F.action == "show_tags")
)
async def show_tags(
    callback: CallbackQuery, 
    state: FSMContext
):
    data = await state.get_data()
    file_id, file_type = get_file_id(callback.message)

    if file_id and file_type:
        await message_alert(
            message=callback.message,
            text="Таги:\n\n" + ", ".join(data["tags"]),
            deley=5
        )
        return
    
    await callback.answer("Неможливо знайти таги до посту")


@add_posts_router.callback_query(
    AddingPostStates.check, 
    AddPostCallback.filter(F.action.in_({"is_hidden", "is_nsfw"}))
)
async def set_special_checks(
    callback: CallbackQuery, callback_data: AddPostCallback, state: FSMContext
):
    if callback_data.action == "is_hidden":
        data = {"is_hidden": not bool(callback_data.data)}
    elif callback_data.action == "is_nsfw":
        data = {"is_nsfw": not bool(callback_data.data)}
    await state.update_data(data)

    data = await state.get_data()
    is_hidden = data.get("is_hidden")
    is_nsfw = data.get("is_nsfw")
    btns = form_check_post_btns(
        is_hidden, is_nsfw, "check_post_info") + [[cancel_adding_post_btn]]

    await callback.message.edit_reply_markup( 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@add_posts_router.callback_query(
    AddingPostStates.check,
    AddPostCallback.filter(
        F.action.in_({"update_post", "update_description", "update_tags"}))
)
async def updating_post_data(
    callback: CallbackQuery, 
    callback_data: AddPostCallback, 
    state: FSMContext
):
    action = callback_data.action
    btns = form_post_adding_move_btns(
        "cancel_updating", from_action="start_update"
    ) + [[cancel_adding_post_btn]]

    if action == "update_post":
        await state.set_state(AddingPostStates.update)
        await state.update_data({"action": "update_post"})
        await callback.message.answer(
            text="Відправте одну фотографію або гіфку", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )
    elif action == "update_description":
        await state.set_state(AddingPostStates.update)
        await state.update_data({"action": "update_description"})
        await callback.message.answer(
            text=("Надішліть тепер підпис до посту (менше 2000 символів)"), 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )
    elif action == "update_tags":
        await state.set_state(AddingPostStates.update)
        await state.update_data({"action": "update_tags"})
        await callback.message.answer(
            text=("Тепер можете додати таги, за "
                  "якими будуть шукати фотографії. "
                  "Вони повинні починатись з '#', а пробіли позначатись '_'. "
                  "Бажано, щоб у кожному тегу було максимум 2-3 слова, які "
                  "описують фотографію\n\n"
                  "Приклад: #природа #ліс #сіра_миш #зелений_дуб "
                  "#вставити_ще_щось_подібне"), 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )


@add_posts_router.callback_query(
    AddingPostStates.check,
    AddPostCallback.filter(F.action == "set_post")
)
async def set_post(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_tg_id = callback.from_user.id
    is_hidden = data.get("is_hidden") or False
    is_nsfw = data.get("is_nsfw") or False
    result = await db.posts.add_one({
        "user_tg_id": user_tg_id,
        "file_id": data["file_id"],
        "file_type": data["file_type"],
        "description": data["description"],
        "tags": data["tags"],
        "words": data["words"],
        "is_hidden": is_hidden,
        "is_nsfw": is_nsfw,
        "complaints": [],
        "reactions": [],
        "timestamp": datetime.now()
    })
    data |= {
        "_id": result.inserted_id, 
        "user_tg_id": user_tg_id, 
        "reactions": [],
        "is_hidden": is_hidden,
        "is_nsfw": is_nsfw
    }

    await state.clear()
    await callback.message.answer("Пост було успішно додано!")

    cur, _ = await db.users.get({"status": {"$in": ["admins", "owner"]}})
    func, kwargs = await make_results_for_message(
        callback.message, data, to_another=True, is_admin=True)

    for admins in await cur.to_list(None):
        try:
            await callback.bot.send_message(
                chat_id=admins["user_tg_id"],
                text="Було додано новий пост!"
            )
            await func(chat_id=admins["user_tg_id"], **kwargs)
        except:
            pass


# cancel action
@add_posts_router.callback_query(
    CancelBtnCallback.filter(F.action == "cancel_add_post"),
)
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Відмінено додавання посту з картинками")