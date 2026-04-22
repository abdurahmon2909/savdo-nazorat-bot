from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

def contact_keyboard() -> ReplyKeyboardMarkup:
    button = KeyboardButton(text="📞 Telefon raqam yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    return markup

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()