import streamlit as st
from streamlit_cookies_controller import CookieController
from streamlit_modal import Modal

import bson
import uuid

from settings import LIMIT
from app.api import get_file, get_user, send_message_to_user
from app.database import db

def add():
    offset = st.session_state.get("offset") | 0
    
    st.session_state.update({"offset": offset + 20})


def mul():
    offset = st.session_state.get("offset")
    
    st.session_state.update({"offset": offset - 20})


def check_user_auth_and_status() -> str | None:
    params = st.query_params
    token = params.get("token")
    user_tg_id = params.get("user_tg_id")
    user_tg_id = bson.Int64(user_tg_id) if user_tg_id else None

    controller = CookieController()
    access_token = controller.get("access_token")

    if not token and not user_tg_id and not access_token:
        return None
    
    result = db.users.find_one({"$or": [
        {"token": token, "user_tg_id": user_tg_id},
        {"access_token": access_token}
    ]})

    if not result:
        return None
    
    if not access_token:
        access_token = str(uuid.uuid4())
        controller.set("access_token", access_token)
        db.users.update_one(
            {"user_tg_id": user_tg_id}, 
            {"$set": {"access_token": access_token}}
        )

    return result["status"]


def filter_sidebar(status: str):
    sidebar = st.sidebar

    sidebar.radio(
        label="Показувати фотографії",
        options=["all", "my", "saved"],
        captions=["Всі", "Свої", "Збережені"]
    )

    checkboxes_keys = {
        "show_nsfw", "show_hidden", "blur_nsfw"
    }
    checkboxes_data = {
        "show_nsfw": ("Показувати 18+", False),
        "show_hidden": ("Показувати приховані", True),
        "blur_nsfw": ("Заблюрувати 18+", True),
    }

    if status not in ["admin", "owner"]:
        checkboxes_keys.difference("show_hidden")

    for checkbox_key in list(checkboxes_keys):
        label, checked = checkboxes_data[checkbox_key]
        sidebar.checkbox(label, checked, checkbox_key)

    sidebar.text_input("Запит на пошук", key="query", max_chars=1000)
    search_btn = sidebar.button("Шукати")

    if search_btn:
        st.rerun()


def post_list():
    offset = 0

    if not st.session_state.get("offset"):
        st.session_state.update({"offset": offset})
    else:
        offset = st.session_state["offset"]

    posts = db.posts.find({})
    count = db.posts.count_documents({})

    for post in posts.sort("timestamp", -1).skip(offset).limit(LIMIT):
        st.divider()

        post_data = get_file(post["file_id"])

        if post["file_type"] in ["animation", "video"]:
            st.video(post_data)
        else:
            st.image(post_data)

        user_id = post["user_tg_id"]
        user_data = get_user(user_id)

        first_name = user_data["result"].get("first_name")
        last_name = user_data["result"].get("last_name")
        username = user_data["result"].get("username")

        publisher = f"{first_name or ''} {last_name or ''}"
        if username:
            st.markdown(f"Опублікував: [{publisher}](https://t.me/{username})")
        else:
            st.markdown(f"Опублікував: [{publisher}](https://t.me/id{user_id})")

        if description := post["description"]:
            st.write(f"Опис: {description}")

        tags = [f"#{tag}" for tag in post["tags"]]
        st.write(" ".join(tags))

        col1, col2 = st.columns(2)

        post_status = post.get("status")
        hide_post_btn = col1.button(
            "Приховати" if post_status != "hidden" else "Відкрити",
            f"hide_post{post['_id']}"
        )

        if hide_post_btn:
            if post_status == "hidden":
                query = {"status": "opened"}
                text = f"Було відкрито пост з айді {post['_id']}"
            else:
                query = {"status": "hidden"}
                text = f"Було приховано пост з айді {post['_id']}"

            db.posts.update_one({"_id": post["_id"]}, {"$set": query})

            if not send_message_to_user(user_id, text):
                st.warning("Не було надіслано повідомлення користувачу")

            st.rerun()

        delete_btn = col2.button("Видалити", f"delete{post['_id']}")

        if delete_btn:
            result = db.posts.delete_one({"_id": post["_id"]})
            
            if result.deleted_count < 1:
                st.warning("Cannot delete post")

            if not send_message_to_user(user_id, "Ваш пост було видалено"):
                st.warning("Cannot send message to user")

            st.rerun()

        show_user_btn = st.button(
            "Показати користувача", f"show_user{post['_id']}:{user_id}")

        if show_user_btn:
            user = db.users.find_one({"user_tg_id": user_id})
            
            if not user:
                st.warning("Не було знайдено користувача")
            else:
                modal = Modal("Дані про користувача", "user-info")
                
                with modal.container():
                    user_status = user['status']
                    st.markdown(
                        f"Користувач: {first_name} {last_name}\n"
                        f"Посилання: https://t.me/{username}\n"
                        f"Статус: {user_status}\n"
                    )
                    action_btn = st.button(
                        "Розблукувати" if user_status == "blocked" else "Заблокувати",
                        f"action{user_id}"
                    )

                    if action_btn:
                        user_status = list(
                            {"blocked", "user"}.difference({user_status}))[0]
                        
                        

            st.rerun()

        st.divider()

    if offset > LIMIT:
        st.button("back", on_click=mul)

    if offset < count and offset >= LIMIT:
        st.button("forward", on_click=add)


def main():
    status = check_user_auth_and_status()

    if not status:
        st.warning("Ви не авторизовані. Авторизуватись можна через бота")
        return
    
    if status not in ["admin", "owner"]:
        st.warning("Ця сторінка поки доступна лише для адміністраторів бота")
        return
    
    filter_sidebar(status)
    post_list()


if __name__ == "__main__":
    main()