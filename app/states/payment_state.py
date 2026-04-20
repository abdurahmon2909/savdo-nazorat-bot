from aiogram.fsm.state import State, StatesGroup


class AddPaymentState(StatesGroup):
    customer = State()
    order = State()
    amount = State()
    confirm = State()