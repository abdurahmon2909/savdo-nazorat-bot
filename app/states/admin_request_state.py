from aiogram.fsm.state import State, StatesGroup


class ManageOrderRequestState(StatesGroup):
    request_id = State()
    decision = State()