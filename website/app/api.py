import io
from PIL import Image, ImageFile, GifImagePlugin
import urllib3

from settings import TOKEN, BOTID

manager = urllib3.PoolManager()


def get_file(file_id: str) -> bytes:
    response: urllib3.BaseHTTPResponse = manager.request(
        "GET",
        f"https://api.telegram.org/bot{TOKEN}/getFile?chat_id={BOTID}&file_id={file_id}"
    )

    if response.status >= 300:
        raise ValueError("Cannot get file")
    
    data: dict = response.json()
    file_path = data["result"]["file_path"]
    response: urllib3.BaseHTTPResponse = manager.request(
        "GET",
        f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    )

    if response.status >= 300:
        raise ValueError("Cannot load file")
    
    return response.data


def get_user(user_tg_id: int) -> dict:
    response: urllib3.HTTPResponse = urllib3.request(
        "GET",
        f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id={user_tg_id}"
    )

    if response.status >= 300:
        raise ValueError("Cannot get user")
    
    return response.json()


def send_message_to_user(user_tg_id: int, text: str) -> bool:
    response: urllib3.HTTPResponse = urllib3.request(
        "POST",
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": user_tg_id,
            "text": text
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status >= 300:
        raise ValueError("Cannot load file")
    
    response = response.json()

    if response["ok"]:
        return True