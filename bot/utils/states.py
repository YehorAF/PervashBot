from aiogram.fsm.state import State, StatesGroup


class AddingPostStates(StatesGroup):
    add_post = State()
    send_several_photos = State()
    add_description = State()
    add_tags = State()
    check = State()
    update = State()


class ComplaintOnPostStates(StatesGroup):
    complaint = State()
    reaction_on_compalaint = State()


class SendComplaintToAdminStates(StatesGroup):
    wait_msg = State()