from aiogram.fsm.state import State, StatesGroup


class AdjustStockState(StatesGroup):
    product = State()
    quantity = State()
    confirm = State()