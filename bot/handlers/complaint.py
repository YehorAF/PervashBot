import asyncio
import bson
from datetime import datetime
import logging
import random

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery,\
    InlineKeyboardMarkup

from handler_operations.using_post import make_results_for_inline,\
    make_results_for_message, parse_request, get_saved_posts
from utils.callbacks import PostReactCallback, ComplaintOnPostCallback,\
    CancelBtnCallback
from utils.database import db
from utils.formatter import form_cancel_btn, form_complaint_btns,\
    form_reaction_on_complaint_btns, form_action_on_complaint_btns
from utils.states import ComplaintOnPostStates

complaint_router = Router(name="complaint_router")


# complaint on post
@complaint_router.callback_query(
    PostReactCallback.filter(F.reaction == "complaint")
)
async def complaint_on_post(
    callback: CallbackQuery, 
    callback_data: PostReactCallback, 
    state: FSMContext
):
    post_id = callback_data.post_id
    _, count = await db.posts.get({"_id": bson.ObjectId(post_id)}, {"_id": 1})

    if count < 1:
        await callback.answer("Цей пост уже видалили", show_alert=True)
        return
    
    user_tg_id = callback.from_user.id
    chat = await callback.bot.get_chat(user_tg_id)

    if not chat:
        await callback.answer("Запустіть бота, щоб залишити скаргу", True)
        return

    show_post_btn = InlineKeyboardButton(
        text="Переглянути пост",
        callback_data=ComplaintOnPostCallback(
            action="show_post", 
            post_id=post_id, 
            user_tg_id=user_tg_id
        ).pack()
    )

    await state.update_data({"post_id": post_id})
    await state.set_state(ComplaintOnPostStates.complaint)

    try:
        await callback.bot.send_message(
            chat_id=user_tg_id,
            text=(
                "Вам не сподобався пост.\n\n"
                "Будь ласка, опишіть чому не сподобався пост"
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=(
                    [[show_post_btn]] + form_cancel_btn("cancel_complaint")
                )
            )
        )
    except:
        await state.clear()
        await callback.answer(
            "Потрібно запустити бота, щоб надіслати скаргу", True)
    else:
        await callback.answer()


@complaint_router.message(F.text, ComplaintOnPostStates.complaint)
async def set_complaint_text(message: Message, state: FSMContext):
    text = message.text
    await state.update_data({"text": text})

    data = await state.get_data()
    btns = form_complaint_btns(data["post_id"])

    await message.answer(
        text=("Надіслати скаргу?\n\nМожна її переписати "
         "(просто напишіть ще раз текст скарги)"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@complaint_router.callback_query(
    ComplaintOnPostCallback.filter(F.action == "complaint"),
    ComplaintOnPostStates.complaint
)
async def send_complaint(
    callback: CallbackQuery, 
    callback_data: ComplaintOnPostCallback,
    state: FSMContext
):
    user_tg_id = callback.from_user.id
    user_full_name = callback.from_user.full_name
    post_id = callback_data.post_id
    data = await state.get_data()
    text = data["text"]

    await db.posts.raw_update(
        {"_id": bson.ObjectId(post_id)},
        {"$push": {"complaints": {
            "user_tg_id": user_tg_id, 
            "text": text,
            "timestamp": datetime.now()
        }}}
    )

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        "Скаргу було надіслано! Скоро її розгляне адміністрація"
    )

    cur, _ = await db.users.get(
        {"status": {"$in": ["admin", "owner"]}}, {"user_tg_id": 1}
    )

    btns = form_reaction_on_complaint_btns(post_id, user_tg_id)
    kb = InlineKeyboardMarkup(inline_keyboard=btns)

    for data in await cur.to_list(None):
        await asyncio.sleep(1)
        await callback.bot.send_message(
            chat_id=data["user_tg_id"],
            text=(
                f"Було надіслано скаргу на пост {post_id} користувачем "
                f"<a href=\"tg://user?id={user_tg_id}\">{user_full_name}</a>\n\n"
                f"Текст скарги:\n{text}"
            ),
            reply_markup=kb,
            parse_mode="HTML"
        )


@complaint_router.callback_query(
    CancelBtnCallback.filter(F.action == "cancel_complaint")
)
async def cancel_complaint(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Написання скарги було відмінено")


# react on complaint
@complaint_router.callback_query(ComplaintOnPostCallback.filter(
    F.action.in_({"delete_post", "reject_complaint"})
))
async def start_reacting_on_complaint(
    callback: CallbackQuery, 
    callback_data: ComplaintOnPostCallback,
    state: FSMContext
):
    action = callback_data.action
    post_id = callback_data.post_id
    user_tg_id = callback_data.user_tg_id

    if action == "delete_post":
        text = "Було видалено через недотримання правил до змісту публікації"
        answer_text = (
            "Напишіть текст з поясненям видалення посту\n\n"
            f"Текст за замовчуванням: {text}"
        )
    elif action == "reject_complaint":
        text = "Було відхилено скаргу через дотримання публікації правил"
        answer_text = (
            "Напишіть текст з поясненям відхилення скарги\n\n"
            f"Текст за замовчуванням: {text}"
        )

    btns = form_cancel_btn("cancel_reacting_on_complant")
    await state.update_data({
        "action": action,
        "post_id": post_id, 
        "user_tg_id": user_tg_id, 
        "text": text
    })
    await state.set_state(ComplaintOnPostStates.reaction_on_compalaint)
    await callback.message.answer(
        text=answer_text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@complaint_router.message(
    F.text, ComplaintOnPostStates.reaction_on_compalaint
)
async def set_description_to_complaint_reaction(
    message: Message, state: FSMContext
):
    text = message.text
    data = await state.get_data()
    btns = (form_action_on_complaint_btns(data) + 
            form_cancel_btn("cancel_reacting_on_complant"))

    await state.update_data({"text": text})
    await message.answer(
        text=f"Виконати дію й надіслати таку відповідь:\n\n {text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


@complaint_router.callback_query(
    ComplaintOnPostCallback.filter(
        F.action.in_({"delete_post_act", "reject_complaint_act"})),
    ComplaintOnPostStates.reaction_on_compalaint
)
async def act_on_complaint(
    callback: CallbackQuery, 
    state: FSMContext
):
    data = await state.get_data()
    await state.clear()

    action = data["action"]
    user_tg_id = data["user_tg_id"]
    post_id = bson.ObjectId(data["post_id"])
    text = data["text"]

    result = await db.posts.raw_update({"_id": post_id}, {
        "$pull": {"complaints": {"user_tg_id": user_tg_id}}
    })

    if result.matched_count < 1:
        await callback.answer()
        await callback.message.answer(
            "Пост і/або скарга були видалені вже видалені"
        )
        return

    if action == "delete_post":
        post = await db.posts.r.find_one_and_delete({"_id": post_id})
        func, kwargs = await make_results_for_message(
            callback.message, post, to_another=True
        )
        del kwargs["reply_markup"]
        kwargs |= {"chat_id": post["user_tg_id"]}
        await func(**kwargs)
        await callback.bot.send_message(
            post["user_tg_id"], 
            text=f"Було видалено ваш пост\n\nПояснення:\n{text}"
        )
    else:
        await callback.bot.send_message(
            user_tg_id,
            text=f"Було відхилено вашу скаргу\n\nПояснення:\n{text}"
        )

    await callback.answer()
    await callback.message.answer("Відповідь було надіслано!")


@complaint_router.callback_query(
    ComplaintOnPostCallback.filter(F.action == "show_post")
)
async def show_post(
    callback: CallbackQuery, callback_data: ComplaintOnPostCallback
):
    post_id = bson.ObjectId(callback_data.post_id)
    cur, count = await db.posts.get({"_id": post_id})

    if count < 1:
        await callback.answer("Пост було видалено")
        return
    
    post = (await cur.to_list(1))[0]
    func, kwargs = await make_results_for_message(callback.message, post)

    del kwargs["reply_markup"]
    await func(**kwargs)


@complaint_router.callback_query(
    CancelBtnCallback.filter(F.action == "cancel_reacting_on_complant")
)
async def cancel_reacting_on_complant(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Дію на скаргу було відмінено!")