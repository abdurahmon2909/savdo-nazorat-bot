# app/utils/helpers.py
import logging
from decimal import Decimal, InvalidOperation
from aiogram.types import Message, CallbackQuery
from app.config import settings


def is_admin(obj: Message | CallbackQuery) -> bool:
    """Foydalanuvchi admin yoki yo‘qligini tekshiradi"""
    return bool(obj.from_user and obj.from_user.id in settings.admin_ids)


def parse_decimal(value: str) -> Decimal | None:
    """Matndan Decimal ga o‘girish, noto‘g‘ri bo‘lsa None"""
    try:
        cleaned = (value or "").strip().replace(",", ".")
        if not cleaned:
            return None
        number = Decimal(cleaned)
        if number <= 0:
            return None
        return number
    except (InvalidOperation, AttributeError):
        return None


def format_number(value: Decimal | float | int | str | None) -> str:
    """Decimalni chiroyli formatlash (1000.00 -> 1000)"""
    if value is None:
        return "0"
    try:
        d = Decimal(str(value))
        text = format(d, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    except Exception:
        return str(value)


def fmt(value) -> str:
    """format_number uchun qisqa nom"""
    return format_number(value)


def log_error(func_name: str, error: Exception) -> None:
    """Xatoliklarni log qilish"""
    logging.exception(f"{func_name} da xato: {error}")