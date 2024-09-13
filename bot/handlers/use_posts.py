import bson
from datetime import datetime
import pymongo

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message, InlineQuery, CallbackQuery,\
    InlineKeyboardMarkup

from handler_operations.using_post import make_results_for_inline,\
    make_results_for_message, parse_request, get_saved_posts, count_reactions
from utils.callbacks import PostReactCallback, PostMoveCallback
from utils.database import db
from utils.formatter import form_reaction_btns

use_posts_router = Router(name="use_posts_router")


# show pictures in inline
@use_posts_router.inline_query(F.query.regexp(r"(pict|my|saved|manage)"))
async def search_picture_via_inline(inline_query: InlineQuery):
    command, offset, query, tags = parse_request(inline_query.query, True)
    query |= {"status": {"$ne": "hidden"}}
    user_tg_id = inline_query.from_user.id
    msg_formatter_kwargs = {}

    if inline_query.chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        query |= {"is_nsfw": {"$ne": True}}
    if command == "my":
        query |= {"user_tg_id": user_tg_id}
        del query["status"]
        msg_formatter_kwargs |= {"is_user": True}
    elif command == "saved":
        saved = await get_saved_posts(user_tg_id)

        if not saved:
            return
    
        query |= {"_id": {"$in": saved}}

    if inline_query.chat_type != ChatType.SENDER:
        msg_formatter_kwargs = {}
    elif inline_query.chat_type == ChatType.SENDER and command == "manage":
        result = await db.users.r.find_one(
            {"user_tg_id": user_tg_id, "status": {"$in": ["admin", "owner"]}}
        )
        msg_formatter_kwargs |= {"is_admin": True if result is not None else False}
        del query["status"]

    cur, count = await db.posts.get(query)

    if count - offset < 1:
        return

    cur = cur.sort("timestamp", -1).skip(offset)
    results = await make_results_for_inline(
        await cur.to_list(50), inline_query.bot, **msg_formatter_kwargs)
    await inline_query.answer(results, cache_time=30, is_personal=True)


# show pictures in message
@use_posts_router.message(Command(commands={"pict", "my", "saved", "manage"}))
async def search_picture_via_command(message: Message):
    command, offset, query, _ = parse_request(message.text, False)
    query |= {"status": {"$ne": "hidden"}}
    user_tg_id = message.from_user.id
    msg_formatter_kwargs = {}

    if command == "my":
        query |= {"user_tg_id": user_tg_id}
        del query["status"]
        msg_formatter_kwargs |= {"is_user": True}
    elif command == "saved":
        saved = await get_saved_posts(user_tg_id)

        if not saved:
            return
        
        query |= {"_id": {"$in": saved}}

    if message.chat.type != ChatType.PRIVATE:
        msg_formatter_kwargs = {}
    elif message.chat.type == ChatType.PRIVATE and command == "manage":
        result = await db.users.r.find_one(
            {"user_tg_id": user_tg_id, "status": {"$in": ["admin", "owner"]}}
        )
        msg_formatter_kwargs |= {"is_admin": True if result is not None else False}
        del query["status"]

    cur, count = await db.posts.get(query)

    if count < 1:
        return

    # is_max = False if count - offset > 1 else True
    # ins_res = await db.requests.add_one({
    #     "tags": tags,
    #     "post_id":  post["_id"],
    #     "offset": offset,
    #     "user_tg_id": user_tg_id, 
    #     "command": command, 
    #     "is_max": is_max,
    #     "timestamp": datetime.now()
    # })
    post = (await cur.sort("timestamp", -1).skip(offset).to_list(1))[0]
    func, kwargs = await make_results_for_message(
        message, post, **msg_formatter_kwargs)
    # func, kwargs = await make_results_for_message(
    #     message, post, str(ins_res.inserted_id), command, offset, is_max)
    await func(**kwargs)


# reacts on photo
@use_posts_router.callback_query(
    PostReactCallback.filter(F.reaction.in_({"positive", "negative"}))
)
async def react_on_photo(
    callback: CallbackQuery, callback_data: PostReactCallback
):
    user_tg_id = callback.from_user.id
    post_id = callback_data.post_id
    post_id_bson = bson.ObjectId(post_id)
    reaction = callback_data.reaction
    diff_reaction = list({"positive", "negative"}.difference({reaction}))[0]

    def is_reaction(reaction: dict):
        if (reaction["user_tg_id"] == user_tg_id and 
            reaction["reaction"] == diff_reaction):
            return True
        return False

    def is_in_reactions(reaction: dict):
        if reaction["user_tg_id"] == user_tg_id:
            return True
        return False

    result = await db.posts.r.find_one_and_update(
        {"_id": post_id_bson}, 
        {"$addToSet": {
            "reactions": {"user_tg_id": user_tg_id, "reaction": reaction}
        }},
        return_document=pymongo.ReturnDocument.BEFORE
    )

    if not result:
        await callback.answer("Пост було видалено")
        return
    
    check_is_reaction = list(filter(is_reaction, result["reactions"]))
    check_is_in_reactions = list(filter(is_in_reactions, result["reactions"]))
    
    if check_is_reaction or not check_is_in_reactions:
        reaction = diff_reaction

    result = await db.posts.r.find_one_and_update(
        {"_id": post_id_bson}, 
        {"$pull": {
            "reactions": {"user_tg_id": user_tg_id, "reaction": reaction}
        }},
        return_document=pymongo.ReturnDocument.AFTER
    )

    # movement_args = {}
    # request_id = callback_data.request_id
    # if request_id:
    #     cur, count = await db.requests.get(
    #         {"_id": bson.ObjectId(request_id)})

    #     if count > 0:
    #         request = (await cur.to_list(1))[0]
    #         movement_args = {
    #             "request_id": request_id,
    #             "command": request["command"],
    #             "offset": request["offset"],
    #             "is_max": request["is_max"]
    #         }

    pos_count, neg_count = count_reactions(result["reactions"])
    btns = form_reaction_btns(post_id, pos_count, neg_count)
    # btns = form_reaction_btns(
    #     post_id, pos_count, neg_count, **movement_args)
    kb = InlineKeyboardMarkup(inline_keyboard=btns)

    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=kb)
    elif message_id := callback.inline_message_id:
        await callback.bot.edit_message_reply_markup(
            inline_message_id = message_id,
            reply_markup=kb
        )
    

# save photo
@use_posts_router.callback_query(
    PostReactCallback.filter(F.reaction == "save")
)
async def save_photo(
    callback: CallbackQuery, callback_data: PostReactCallback
):
    user_tg_id = callback.from_user.id
    post_id = bson.ObjectId(callback_data.post_id)

    cur, _ = await db.users.get({"user_tg_id": user_tg_id}, {"saved": 1})
    user = (await cur.to_list(1))[0]

    if post_id in user["saved"]:
        await db.users.raw_update(
            {"_id": user["_id"]}, {"$pull": {"saved": post_id}})
        text = "Блін... Було видалено зі збережних..."
    else:
        await db.users.raw_update(
            {"user_tg_id": user_tg_id}, {"$push": {"saved": post_id}})
        text = "Ура! Було додано до збережних!"

    await callback.answer(text, show_alert=True)


@use_posts_router.message(Command("one_my"))
async def get_one_my(message: Message):
    if message.chat.type not in [ChatType.PRIVATE, ChatType.SENDER]:
        return
    
    user_tg_id = message.from_user.id
    post_id = message.text.split()[-1]
    
    if not bson.ObjectId.is_valid(post_id):
        return
    
    post_id = bson.ObjectId(post_id)
    post = await db.posts.r.find_one(
        {"_id": post_id, "user_tg_id": user_tg_id}
    )

    if not post:
        await message.answer("Не вдалось знайти подібний пост")
        return
    
    func, kwargs = await make_results_for_message(message, post, is_user = True)
    await func(**kwargs)


# moves
# @use_posts_router.callback_query(
#     PostMoveCallback.filter(F.move.in_({"back", "forward"}))
# )
# async def move_posts(
#     callback: CallbackQuery, callback_data: PostMoveCallback
# ):
#     request_id = callback_data.request_id
#     bson_request_id = bson.ObjectId(request_id)
#     cur, count = await db.requests.get({"_id": bson_request_id})

#     if count < 1:
#         return

#     request = (await cur.to_list(1))[0]
#     movement = callback_data.move
#     offset = request["offset"]
#     command = request["command"]
#     tags = request["tags"]
#     user_tg_id = request["user_tg_id"]
#     is_max = request["is_max"]

#     if movement == "forward" and is_max:
#         return
#     elif movement == "forward":
#         offset += 1

#     if movement == "back" and offset < 1:
#         return
#     elif movement == "back":
#         offset -= 1

#     post_id = bson.ObjectId(request["post_id"])
#     query = {}

#     if tags:
#         query |= {"words": {"$in": tags}}

#     if command == "my":
#         query |= {"user_tg_id": user_tg_id}
#     elif command == "saved":
#         saved = await get_saved_posts(user_tg_id)

#         if not saved:
#             return
        
#         query |= {"_id": {"$in": saved}}

#     cur, count = await db.posts.get(query)
#     posts = (await cur.sort({"timestamp": 1}).skip(offset).to_list(1))

#     if not posts:
#         await callback.answer("Нема постів")
    
#     post = posts[0]
#     is_max = False if count - offset > 1 else True

#     await db.requests.update(
#         {"_id": bson_request_id},
#         {"offset": offset, "is_max": is_max, "timestamp": datetime.now()}
#     )

#     func, kwargs = await make_results_for_message(
#         message=callback.message,
#         post=post,
#         request_id=request_id,
#         command=command,
#         offset=offset
#     )
#     await callback.answer()
#     await func(**kwargs)