from decimal import Decimal
from aiogram import Bot

from app.config import settings
from app.utils.helpers import format_number


async def send_low_stock_alert(
    bot: Bot,
    product_name: str,
    stock_quantity: Decimal,
    unit: str,
) -> None:
    threshold = settings.low_stock_threshold
    if Decimal(str(stock_quantity)) > threshold:
        return

    text = (
        "⚠️ Mahsulot qoldig'i kamaydi.\n\n"
        f"Mahsulot: {product_name}\n"
        f"Qoldiq: {format_number(stock_quantity)} {unit}\n"
        f"Chegara: {format_number(threshold)} {unit}"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass