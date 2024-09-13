from aiogram import Bot
from aiogram.types import Message, InlineQuery, InlineQueryResultPhoto,\
    InlineQueryResultGif, InlineQueryResultVideo, InlineKeyboardMarkup

from utils.database import db
from utils.formatter import form_reaction_btns, form_manage_post_btns


async def make_description(
    description: str, is_hidden: bool, user_tg_id: str, bot: Bot
):
    if not is_hidden:
        chat = await bot.get_chat(user_tg_id)
        name = chat.full_name if chat else user_tg_id
        description += (
            f"\n\nОпублікував: <a href=\"tg://user?id={user_tg_id}\">"
            f"{name}</a>"
        )

    return description


def parse_request(text: str, is_inline: bool):
    data = text.split(" ")

    if is_inline:
        command = data[0]
    else:
        command = data[0].replace("/", "").replace("@", " ").split(" ")[0]

    offset = 0
    tags = []

    if len(data) > 1:
        offset = data[1]
        try: 
            offset = int(offset)
        except:
            tags += [offset]
            offset = 0
    if len(data) > 2:
        tags = data[2:]

    tags = [tag.lower() for tag in tags]

    if not tags:
        query = {}
    else:
        query = {"words": {"$in": tags}}

    return command, offset, query, tags


async def make_results_for_inline(
    posts, bot: Bot, is_user: bool = False, is_admin: bool = False 
):
    results = []
    for post in posts:
        pos_reacts, neg_reacts = count_reactions(post["reactions"])
        post_id = str(post["_id"])
        user_tg_id = post["user_tg_id"]
        btns = form_reaction_btns(
            post_id, pos_reacts=pos_reacts, neg_reacts=neg_reacts
        )

        if is_user:
            btns += form_manage_post_btns(post_id, hiddened_by=post["status"])
        elif is_admin:
            btns += form_manage_post_btns(
                post_id, user_tg_id, True, post["status"]
            )

        description = await make_description(
            post["description"], post["is_hidden"], user_tg_id, bot)

        if post["file_type"] == "photo":
            results.append(InlineQueryResultPhoto(
                id=post_id,
                photo_url=post["file_id"],
                thumbnail_url=post["file_id"],
                caption=description,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
                parse_mode="HTML",
            ))
        elif post["file_type"] == "animation":
            results.append(InlineQueryResultGif(
                id=post_id,
                gif_url=post["file_id"],
                thumbnail_url=post["file_id"],
                caption=description,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
                parse_mode="HTML"
            ))
        elif post["file_type"] == "video":
            results.append(InlineQueryResultVideo(
                id=post_id,
                video_url=post["file_id"],
                mime_type="video/mp4",
                thumbnail_url=post["file_id"],
                title=post["description"][:64] or "¯\_(ツ)_/¯",
                caption=description,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
                parse_mode="HTML"
            ))

    return results


def count_reactions(reactions: list[dict]):
    neg_reactions = 0
    pos_reactions = 0

    for reaction in reactions:
        if reaction["reaction"] == "positive":
            pos_reactions += 1
        else:
            neg_reactions += 1

    return pos_reactions, neg_reactions


async def make_results_for_message(
    message: Message,  
    post: dict,
    request_id: str = "", 
    command: str = "", 
    offset: int = 0, 
    is_max: bool = "",
    to_another: bool = False, 
    is_user: bool = False, 
    is_admin: bool = False
):
    pos_reacts, neg_reacts = count_reactions(post["reactions"])
    post_id = str(post["_id"])
    user_tg_id = post["user_tg_id"]
    btns = form_reaction_btns(
        post_id=post_id, 
        pos_reacts=pos_reacts,
        neg_reacts=neg_reacts,
        request_id=str(request_id),
        command=command,
        offset=offset,
        is_max=is_max
    )

    if is_user:
        btns += form_manage_post_btns(post_id, hiddened_by=post["status"])
    elif is_admin:
        btns += form_manage_post_btns(
            post_id, user_tg_id, True, post["status"]
        )

    description = await make_description(
        post["description"], post["is_hidden"], user_tg_id, message.bot)
    kwargs = {
        "caption": description,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=btns),
        "has_spoiler": post["is_nsfw"],
        "parse_mode": "HTML"
    }

    if post["file_type"] == "photo":
        func = message.bot.send_photo if to_another else message.answer_photo
        kwargs |= {"photo": post["file_id"]}
    elif post["file_type"] == "animation":
        func = message.bot.send_animation if to_another else message.answer_animation
        kwargs |= {"animation": post["file_id"]}
    elif post["file_type"] == "video":
        func = message.bot.send_video if to_another else message.answer_video
        kwargs |= {"video": post["file_id"]}

    return func, kwargs


async def get_saved_posts(user_tg_id: int):
    cur, count = await db.users.get(
        {"user_tg_id": user_tg_id}, {"saved": 1})

    if count < 1:
        return []

    res = (await cur.to_list(1))[0]
    saved = res["saved"]

    return saved