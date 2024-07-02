import bson
# from bs4 import BeautifulSoup
from datetime import datetime
import random
from redis.asyncio import Redis
# import requests
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, URLInputFile,\
    InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery,\
    InlineQueryResultPhoto

from tools.callbacks import PhotoCallback
from tools.database import Database, redis
from tools.filters import PhotoFilter
from tools.formatter import form_react_btns
from tools.text import INLINE_QUERIES, INLINE_QUERIES_DESCRIPTION, NSFW


photos_router = Router()


@photos_router.message(Command(commands=INLINE_QUERIES), PhotoFilter(redis))
# @photos_router.message()
async def get_picture(message: Message, db: Database):
    command = message.text.replace("/", "").replace("@", " ").split()[0]
    photos_cur, count = await db.photos.get({"type": command})
    skip = random.randrange(0, count)
    photos = await photos_cur.skip(skip).to_list(3)
    is_sended = False
    tries = 0

    while not is_sended and tries < 3:
        try:
            photo_id = photos[tries]["_id"]
            _, pos_count = await db.reactions.get(
                {"photo_id": photo_id, "reaction": "positive"})
            _, neg_count = await db.reactions.get(
                {"photo_id": photo_id, "reaction": "negative"})
            btns = form_react_btns(
                {"photo_id": photo_id, "pos": pos_count, "neg": neg_count})
            await message.reply_photo(
                photo=URLInputFile(photos[tries]["link"]),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
                has_spoiler=photos[tries].get("nsfw")
            )
        except Exception as ex_:
            logging.error(ex_)
            tries += 1
        else:
            is_sended = True

    if tries >= 3:
        await message.answer("Щось пішло не так... Спробуйте трохи пізніше")


@photos_router.inline_query(F.query.in_(INLINE_QUERIES))
async def get_pictures_inl(inline_query: InlineQuery, db: Database):
    query = inline_query.query

    if query in NSFW and inline_query.chat_type not in ["private", "sender"]:
        return

    photos_cur, count = await db.photos.get({"type": query})
    skip = random.randrange(0, count)
    photos = await photos_cur.skip(skip).to_list(50)
    results = []

    for photo in photos:
        photo_id = photo["_id"]
        _, pos_count = await db.reactions.get(
            {"photo_id": photo_id, "reaction": "positive"})
        _, neg_count = await db.reactions.get(
            {"photo_id": photo_id, "reaction": "negative"})
        btns = form_react_btns(
            {"photo_id": photo_id, "pos": pos_count, "neg": neg_count})
        results.append(InlineQueryResultPhoto(
            id=str(photo_id),
            photo_url=photo["link"],
            thumbnail_url=photo["link"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        ))

    await inline_query.answer(results, cache_time=30, is_personal=True)


# @photos_router.inline_query(F.query.startswith(":"))
# async def get_pictures_from_google(inline_query: InlineQuery, db: Database):
#     query = inline_query.query.split(":")[-1].strip()

#     response: requests.Response = requests.get("https://www.google.com/")
#     soup = BeautifulSoup(response.text, "lxml")
#     el = soup.find("input", {"name": "iflsig"})
#     sig = el.get("value")

#     response: requests.Response = requests.get(
#         f"https://www.google.com/search?ie=ISO-8859-1&hl=uk&q={query}&tbm=isch&iflsig={sig}"
#     )
#     soup = BeautifulSoup(response.text, "lxml")
#     elments = soup.select("a.gOJHif")
#     link = elments[-1].get("href")

#     print("\n\nGet pict page\n\n")

#     response: requests.Response = requests.get("https://www.google.com" + link)
#     soup = BeautifulSoup(response.text, "lxml")
#     t = soup.select("div.zhqPEd a")[-1].get("href")

#     print("\n\nSet smth\n\n")

#     response: requests.Response = requests.get("https://www.google.com" + t)
#     soup = BeautifulSoup(response.text, "lxml")
#     sig = soup.find("input", {"name": "sig"}).get("value")

#     print("\n\nSet smth2\n\n")

#     response: requests.Response = requests.get(f"https://www.google.com/setprefs?sig={sig}&safeui=off&submit-button=Підтвердити", cookies=response.cookies)

#     page = random.randrange(20, 100, 20)
#     response: requests.Response = requests.get(
#         f"https://www.google.com/search?ie=ISO-8859-1&hl=uk&q={query}&tbm=isch&sig={sig}&start={page}&sa=N", cookies=response.cookies   
#     )

#     print("\n\nGet pictures\n\n")

#     soup = BeautifulSoup(response.text, "lxml")
#     imgs = soup.select("img.DS1iW")
#     results = []

#     for i, img in enumerate(imgs):
#         src = img.get("src")
#         print(f"\n\n{src}\n\n")
#         results.append(InlineQueryResultPhoto(
#             id=str(i),
#             photo_url=src,
#             thumbnail_url=src
#         ))

#     await inline_query.answer(results, cache_time=30, is_personal=True)


@photos_router.inline_query()
async def get_pictires_without_query(inline_query: InlineQuery, db: Database):
    photos_cur, count = await db.photos.get({"nsfw": {"$ne": True}})
    skip = random.randrange(0, count)
    photos = await photos_cur.skip(skip).to_list(50)
    results = []

    for photo in photos:
        photo_id = photo["_id"]
        _, pos_count = await db.reactions.get(
            {"photo_id": photo_id, "reaction": "positive"})
        _, neg_count = await db.reactions.get(
            {"photo_id": photo_id, "reaction": "negative"})
        btns = form_react_btns(
            {"photo_id": photo_id, "pos": pos_count, "neg": neg_count})
        results.append(InlineQueryResultPhoto(
            id=str(photo["_id"]),
            photo_url=photo["link"],
            thumbnail_url=photo["link"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        ))

    await inline_query.answer(results, cache_time=30, is_personal=True)


@photos_router.callback_query(
    PhotoCallback.filter(F.action == "react")
)
async def set_reaction(
    callback: CallbackQuery, callback_data: PhotoCallback, db: Database
):
    reaction = callback_data.reaction
    photo_id = bson.ObjectId(callback_data.photo_id)
    user_tg_id = callback.from_user.id

    _, count = await db.reactions.get({
        "user_tg_id": user_tg_id, 
        "photo_id": photo_id,
        "reaction": reaction
    })

    if count > 0:
        reaction = ""

    await db.reactions.update(
        query={"user_tg_id": user_tg_id, "photo_id": photo_id}, 
        data={
            "user_tg_id": user_tg_id, 
            "photo_id": photo_id, 
            "reaction": reaction
        }, 
        upsert=True
    )

    _, pos_count = await db.reactions.get(
        {"photo_id": photo_id, "reaction": "positive"})
    _, neg_count = await db.reactions.get(
        {"photo_id": photo_id, "reaction": "negative"})
    btns = form_react_btns(
        {"photo_id": photo_id, "pos": pos_count, "neg": neg_count})
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except:
        await callback.bot.edit_message_reply_markup(
            inline_message_id=callback.inline_message_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )