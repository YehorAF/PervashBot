from datetime import datetime
from redis.asyncio import Redis

from aiogram import Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup,\
    InlineKeyboardButton

from tools.callbacks import ChatSettingsCallback
from tools.database import Database
from tools.filters import AdminMessageFilter, AdminCallbackFilter
from tools.formatter import form_chat_settings_btns
from tools.text import CHAT_SETTINGS, CHAT_SETTINGS_DESCRIPTION,\
    LIMITS, LIMITS_DESCRIPTION


group_router = Router()


@group_router.message(Command("start_group"), AdminMessageFilter())
async def start(message: Message, db: Database, redis: Redis):
    chat = message.chat
    
    _, count = await db.groups.get({"chat_tg_id": chat.id})
    if count > 0:
        return
    
    # allowed = ["anime_girl", "anime_ero", "monkey", "cat", "nsfw"]

    await db.groups.add_one({
        "chat_tg_id": chat.id, 
        # "allowed": allowed
        "show_nsfw": True
    })
    await redis.hset(
        f"group-{chat.id}", 
        mapping={"show_nsfw": "show_nsfw", "lim": "unlim"}
        # mapping={"allowed": "-".join(allowed), "lim": "unlim"}
    )
    await message.answer("Групу було зарєстровано")


@group_router.message(Command("chat_settings"), AdminMessageFilter())
async def get_chat_settings(message: Message, db: Database):
    user_id = message.from_user.id
    chat = message.chat
    
    _, count = await db.groups.get({"chat_tg_id": chat.id})
    if count < 1:
        await message.answer(
            "Необхідно зареєструвати чат за допомогою команди /start_group")
        return
    
    btns = form_chat_settings_btns(
        CHAT_SETTINGS_DESCRIPTION, chat.id, user_id)
    
    await message.answer(
        text="Виберіть секцію налаштування", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@group_router.callback_query(
    ChatSettingsCallback.filter(F.action == "go_back_to_settings"), 
    AdminCallbackFilter()
)
async def get_chat_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat = callback.message.chat
    
    btns = form_chat_settings_btns(
        CHAT_SETTINGS_DESCRIPTION, chat.id, user_id)
    
    await callback.message.edit_text(
        text="Виберіть секцію налаштування", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@group_router.callback_query(
    ChatSettingsCallback.filter(F.action == "set_limit"), AdminCallbackFilter())
async def set_limit_msg(
    callback: CallbackQuery, callback_data: ChatSettingsCallback
):
    user_id = callback.from_user.id
    chat_id = callback_data.chat_id
    
    btns = form_chat_settings_btns(LIMITS_DESCRIPTION, chat_id, user_id, 3)
    btns.append([InlineKeyboardButton(
        text="Повернутися", 
        callback_data=ChatSettingsCallback(
            action="go_back_to_settings", 
            user_id=user_id, 
            chat_id=chat_id, 
            selected=False
        ).pack()
    )])

    await callback.message.edit_text(
        text="Оберіть ліміт на надсилання картинок",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@group_router.callback_query(
    ChatSettingsCallback.filter(F.action.in_(LIMITS)), AdminCallbackFilter())
async def set_limit(
    callback: CallbackQuery, 
    callback_data: ChatSettingsCallback, 
    db: Database,
    redis: Redis
):
    user_id = callback.from_user.id
    chat_id = callback_data.chat_id
    lim = callback_data.action

    hashed = await redis.hgetall(f"group-{chat_id}")
    use_nsfw = hashed.get(b"show_nsfw").decode()

    if lim == "unlim":
        data = {"lim": False}
        r_data = {"lim": "unlim", "show_nsfw": use_nsfw}
    else:
        _, amount, time = tuple(lim.split("-"))
        dt = datetime.now().strftime("%d.%m.%Y-%H:%M:%S")
        data = {
            "lim": True, "max": amount, "reboot": time
        }
        r_data = data | {
            "set_time": dt, "count": 0, "lim": "lim", "show_nsfw": use_nsfw
        }

    await redis.hmset(f"group-{chat_id}", r_data)
    await db.groups.update({"chat_tg_id": chat_id}, data)

    btns = form_chat_settings_btns(
        CHAT_SETTINGS_DESCRIPTION, chat_id, user_id)
    
    await callback.message.edit_text(
        text=(
            f"Виставлено ліміт: {LIMITS_DESCRIPTION[lim]}\n\n"
            "Виберіть секцію налаштування"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@group_router.message(Command("limit"), AdminMessageFilter())
async def set_limit(message: Message, db: Database, redis: Redis):
    chat = message.chat
    
    _, count = await db.groups.get({"chat_tg_id": chat.id})
    if count < 1:
        await message.answer(
            "Необхідно зареєструвати чат за допомогою команди /start_group")
        return
    
    lim = message.text.split()
    hashed = await redis.hgetall(f"group-{chat.id}")
    use_nsfw = hashed.get(b"show_nsfw").decode()

    if lim[1] == "unlim":
        data = {"lim": False}
        r_data = {"lim": "unlim", "show_nsfw": use_nsfw}
        lim = "Без ліміту"
    else:
        try:
            amount = int(lim[1])
            time = int(lim[2])
            if amount < 1 or time < 1:
                raise ValueError()
        except:
            return
        dt = datetime.now().strftime("%d.%m.%Y-%H:%M:%S")
        data = {"lim": True, "max": amount, "reboot": time}
        r_data = data | {
            "set_time": dt, "count": 0, "lim": "lim", "show_nsfw": use_nsfw}
        lim = f"{amount} на {time}хв"

    await redis.hmset(f"group-{chat.id}", r_data)
    await db.groups.update({"chat_tg_id": chat.id}, data)
    await message.answer(f"Виставлено ліміт: {lim}")


@group_router.callback_query(
    ChatSettingsCallback.filter(F.action == "set_filters"), AdminCallbackFilter())
async def set_filters_msg(
    callback: CallbackQuery, 
    callback_data: ChatSettingsCallback, 
    db: Database
):
    user_id = callback.from_user.id
    chat_id = callback_data.chat_id

    btn_text = "Показувати NSFW: "
    use_nsfw = "show_nsfw"

    data, _ = await db.groups.get({"chat_tg_id": chat_id}, {"show_nsfw": 1})
    data =  (await data.to_list(None))[0]

    if data.get("show_nsfw"):
        btn_text += "✅"
        use_nsfw = "hide_nsfw"
    else:
        btn_text += "❌"

    btns = form_chat_settings_btns(
        {use_nsfw: btn_text}, chat_id, user_id)
    btns.append([InlineKeyboardButton(
        text="Повернутися", 
        callback_data=ChatSettingsCallback(
            action="go_back_to_settings", 
            user_id=user_id, 
            chat_id=chat_id, 
            selected=False
        ).pack()
    )])
    
    await callback.message.edit_text(
        text="Оберіть фільтри для картинок",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@group_router.callback_query(
    ChatSettingsCallback.filter(F.action.in_(["show_nsfw", "hide_nsfw"])), 
    AdminCallbackFilter()
)
async def set_nsfw(
    callback: CallbackQuery, 
    callback_data: ChatSettingsCallback, 
    db: Database, 
    redis: Redis
):
    user_id = callback.from_user.id
    chat_id = callback_data.chat_id
    nsfw_flag = callback_data.action

    emj, neg_use_nsfw, is_set_nsfw = {
        "show_nsfw": ("✅", "hide_nsfw", True), 
        "hide_nsfw": ("❌", "show_nsfw", False)
    }[nsfw_flag]
    btn_text = "Показувати NSFW: " + emj
    btns = form_chat_settings_btns(
        {neg_use_nsfw: btn_text}, chat_id, user_id)
    btns.append([InlineKeyboardButton(
        text="Повернутися", 
        callback_data=ChatSettingsCallback(
            action="go_back_to_settings", 
            user_id=user_id, 
            chat_id=chat_id, 
            selected=False
        ).pack()
    )])
    
    hashed = await redis.hgetall(f"group-{chat_id}")
    await redis.hmset(f"group-{chat_id}", {
        "lim": hashed.get(b"lim") or "",
        "max": hashed.get(b"max") or "",
        "reboot": hashed.get(b"reboot") or "",
        "show_nsfw": nsfw_flag
    })
    await db.groups.update({"chat_tg_id": chat_id}, {"show_nsfw": is_set_nsfw})
    await callback.message.edit_text(
        text="Оберіть фільтри для картинок",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )