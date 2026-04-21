# app/utils/timezone.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

def now_utc() -> datetime:
    """Hozirgi UTC vaqt"""
    return datetime.now(timezone.utc)

def utc_to_tashkent(dt: datetime) -> datetime:
    """UTC dan Toshkent vaqtiga"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TASHKENT_TZ)

def format_datetime_tashkent(dt: datetime) -> str:
    """Toshkent vaqtida formatlash"""
    local = utc_to_tashkent(dt)
    return local.strftime("%d-%m-%Y %H:%M")