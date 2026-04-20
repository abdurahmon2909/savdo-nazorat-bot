from decimal import Decimal

from aiogram import Bot

from app.config import settings

LOW_STOCK_THRESHOLD = Decimal("5")


def format_number(value: Decimal | float | int | str) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


async def send_low_stock_alert(
    bot: Bot,
    product_name: str,
    stock_quantity: Decimal,
    unit: str,
) -> None:
    if Decimal(str(stock_quantity)) > LOW_STOCK_THRESHOLD:
        return

    text = (
        "⚠️ Mahsulot qoldig'i kamaydi.\n\n"
        f"Mahsulot: {product_name}\n"
        f"Qoldiq: {format_number(stock_quantity)} {unit}\n"
        f"Chegara: {format_number(LOW_STOCK_THRESHOLD)} {unit}"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass