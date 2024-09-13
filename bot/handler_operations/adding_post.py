from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from utils.callbacks import AddPostCallback, CancelBtnCallback
from utils.database import redis
from utils.notifiers import message_alert
from utils.states import AddingPostStates
from utils.utils import get_file_id


async def add_media_to_storage(message: Message, state: FSMContext):
    lock = redis.lock(message.from_user.id)

    async with lock:
        state_name = await state.get_state()
        if state_name != "AddingPostStates:send_several_photos":
            await state.set_state(AddingPostStates.send_several_photos)

    if (message.media_group_id and 
        state_name != "AddingPostStates:send_several_photos"):
        await message_alert(
            message, "Необхідно надіслати лише одну фотографію!")
        await state.set_state(AddingPostStates.add_post)
        raise ValueError("Too much files")
    elif state_name == "AddingPostStates:send_several_photos":
        raise ValueError("Handling additionsl files to media group")

    if not message.photo and not message.animation and not message.video:
        await message_alert(
            message, "Необхідно надіслати фотографію або анімацію!")
        raise TypeError("Not such type of message content")

    file_id, file_type = get_file_id(message)
    await state.update_data({"file_id": file_id, "file_type": file_type})


async def add_description_to_storage(message: Message, state: FSMContext):
    if not message.text or len(message.text) > 2000:
        await message_alert(
            message, "Необхідно текст з кількістю літер, яка менше 2000")
        raise ValueError("Too large description")
    
    await state.update_data({"description": message.text})


async def add_tags_to_storage(message: Message, state: FSMContext):
    tags = message.text.replace(" ", "").split("#")[1:]
    words = []
    for tag in tags:
        words += tag.lower().split("_")

    await state.update_data({"tags": tags, "words": words})
    await state.set_state(AddingPostStates.check)