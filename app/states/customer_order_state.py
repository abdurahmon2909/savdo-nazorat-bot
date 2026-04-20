from aiogram.fsm.state import State, StatesGroup


class CreateCustomerOrderRequestState(StatesGroup):
    category = State()
    product = State()
    quantity_custom = State()
    add_more = State()
    payment_type = State()
    confirm = State()