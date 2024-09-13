import bson

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup,\
    InlineKeyboardButton

from handler_operations.using_post import make_results_for_message
from utils.callbacks import PostManageCallback, CancelBtnCallback
from utils.database import db

manage_posts_router = Router(name="manage_posts_router")


@manage_posts_router.callback_query(
    PostManageCallback.filter(F.action.in_({"delete_post", "ban_user"}))
)
async def starting_delete_post(
    callback: CallbackQuery, callback_data: PostManageCallback
):
    action = callback_data.action
    post_id = callback_data.post_id
    user_tg_id = callback_data.user_tg_id

    if action == "delete_post":
        msg_text = "Точно хочете видалити потс?"
        btn_text = "Остаточно видалити"
        action = "dfntl_dlt_post"
    else:
        msg_text = "Точно хочете заблокувати користувача"
        btn_text = "Заблокувати користувача"
        action = "dfntl_ban_user"

    manage_btn = InlineKeyboardButton(
        text=btn_text,
        callback_data=PostManageCallback(
            action=action, post_id=post_id, user_tg_id=user_tg_id
        ).pack()
    )
    cancel_btn = InlineKeyboardButton(
        text="Відмінити",
        callback_data=CancelBtnCallback(action="cancel_manage_action").pack()
    )
    ikb = InlineKeyboardMarkup(inline_keyboard=[[manage_btn, cancel_btn]])
    await callback.answer()
    if callback.message:
        await callback.message.answer(msg_text, reply_markup=ikb)
    else:
        chat_id = callback.from_user.id
        await callback.bot.send_message(chat_id, msg_text, reply_markup=ikb)


@manage_posts_router.callback_query(
    PostManageCallback.filter(F.action == "dfntl_dlt_post")
)
async def delete_post(
    callback: CallbackQuery, callback_data: PostManageCallback
):
    user_tg_id = callback.from_user.id

    result = await db.users.r.find_one(
        {"user_tg_id": user_tg_id, "status": {"$in": ["admin", "owner"]}}
    )
    if result is None:
        await callback.answer(
            "Неможливо видалити пост, бо ти не є адміністратором", True
        )
        return
    
    post_id = callback_data.post_id
    post_owner_id = callback_data.user_tg_id

    post = await db.posts.r.find_one_and_delete(
        {"_id": bson.ObjectId(post_id)}
    )
    if post is None:
        await callback.answer(
            f"Чомусь не вдається видалити цей пост: {post_id}", True
        )
        return
    
    if post_owner_id != user_tg_id:
        try:
            func, kwargs = await make_results_for_message(
                callback.message, post, to_another=True
            )
            del kwargs["reply_markup"]
            await callback.bot.send_message(
                post_owner_id, "Ваш пост було видалено"
            )
            await func(chat_id=post_owner_id, **kwargs)
        except:
            pass
    
    await callback.answer()
    await callback.message.edit_text("Пост було успішно видалено!")


@manage_posts_router.callback_query(
    PostManageCallback.filter(F.action == "dfntl_ban_user")
)
async def block_user(
    callback: CallbackQuery, callback_data: PostManageCallback
):
    user_tg_id = callback.from_user.id

    result = await db.users.r.find_one(
        {"user_tg_id": user_tg_id, "status": {"$in": ["admin", "owner"]}}
    )
    if result is None:
        await callback.answer(
            "Неможливо видалити пост, бо ти не є адміністратором", True
        )
        return
    
    if result["status"] == "owner":
        status_query = {"$nin": ["owner"]}
    else:
        status_query = {"$nin": ["admin", "owner"]}

    baned_user_id = callback_data.user_tg_id
    result = await db.users.update(
        {"user_tg_id": baned_user_id, "status": status_query}, 
        {"status": "blocked"}
    )
    
    if result.modified_count < 1:
        await callback.answer(
            f"Чомусь не вдалось заблокувати користувача: {baned_user_id}"
        )
        return
    
    try:
        await callback.bot.send_message(
            baned_user_id, "Вас було заблоковано!"
        )
    except:
        pass
    
    await db.posts.update(
        {"user_tg_id": baned_user_id}, {"status": "hidden"})
    await callback.message.edit_text("Користувача було заблоковано")


@manage_posts_router.callback_query(
    CancelBtnCallback.filter(F.action == "cancel_manage_action")
)
async def cancel(callback: CallbackQuery):
    await callback.message.edit_text("Дію було відмінено")


@manage_posts_router.callback_query(
    PostManageCallback.filter(F.action.regexp(r"(hidden|opened)_by_\w+"))
)
async def hide_post(
    callback: CallbackQuery, callback_data: PostManageCallback
):
    action = callback_data.action
    text = "приховано" if action.find("hidden") != -1 else "відкрито"
    post_id = bson.ObjectId(callback_data.post_id)
    user_tg_id = callback.from_user.id

    query = {"_id": post_id, "user_tg_id": user_tg_id}
    data = {"status": action}

    if action in ["hidden_by_admin", "opened_by_admin"]:
        _, count = await db.users.get(
            {"user_tg_id": user_tg_id, "status": {"$in": ["admin", "owner"]}}
        )
        if count < 1:
            await callback.answer("Нема прав на подібні дії")
            return

        query |= {"user_tg_id": callback_data.user_tg_id}
        data |= {"admin_action_by": user_tg_id}

    result = await db.posts.update(query, data)

    if result.modified_count < 1:
        await callback.answer("Не вдалось виконати дію", True)
        return
    
    await callback.answer(f"Пост було {text}!", True)

    if action in ["hidden_by_admin", "opened_by_admin"]:
        await callback.bot.send_message(
            callback_data.user_tg_id,
            f"Ваш пост було {text} адміністратором: {post_id}"
        )