from aiogram.fsm.state import State, StatesGroup


class CreateOrderState(StatesGroup):
    customer = State()
    product = State()
    quantity = State()
    add_more = State()
    payment_type = State()
    confirm = State()