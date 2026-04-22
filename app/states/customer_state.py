from aiogram.fsm.state import State, StatesGroup


class AddCustomerState(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    note = State()


class SearchCustomerState(StatesGroup):
    query = State()


class EditCustomerState(StatesGroup):
    waiting_for_value = State()