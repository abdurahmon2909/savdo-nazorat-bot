from aiogram.fsm.state import State, StatesGroup


class EditProductPriceState(StatesGroup):
    product_id = State()
    new_price = State()


class AddProductStockState(StatesGroup):
    product_id = State()
    add_quantity = State()


class ArchiveProductState(StatesGroup):
    product_id = State()
    confirm = State()