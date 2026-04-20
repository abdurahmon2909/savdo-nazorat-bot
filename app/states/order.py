from aiogram.fsm.state import State, StatesGroup


class CreateOrderState(StatesGroup):
    customer = State()
    product = State()
    quantity = State()
    confirm = State()