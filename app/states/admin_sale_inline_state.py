from aiogram.fsm.state import State, StatesGroup


class AdminInlineSaleState(StatesGroup):
    customer = State()
    category = State()
    product = State()
    quantity_custom = State()
    add_more = State()
    payment_type = State()
    confirm = State()


class AdminInlinePaymentState(StatesGroup):
    customer = State()
    order = State()
    custom_amount = State()