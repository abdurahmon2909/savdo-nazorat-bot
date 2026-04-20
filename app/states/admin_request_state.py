from aiogram.fsm.state import State, StatesGroup


class CreateCustomerOrderRequestState(StatesGroup):
    product = State()
    quantity = State()
    add_more = State()
    payment_type = State()
    confirm = State()