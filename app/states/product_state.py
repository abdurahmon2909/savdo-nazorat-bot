from aiogram.fsm.state import State, StatesGroup


class AddProductState(StatesGroup):
    name = State()
    category = State()
    unit = State()
    sell_price = State()
    cost_price = State()
    stock_quantity = State()


class SearchProductState(StatesGroup):
    query = State()