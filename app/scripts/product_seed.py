import asyncio
from decimal import Decimal

from app.db import SessionLocal
from app.models.product import Product


DATA = [
    # name, price, stock, category
    ("25 Kg Anor", 12000, 24, "paket"),
    ("10 Kg Anor", 12000, 27, "paket"),
    ("5 Kg Anor", 7500, 40, "paket"),
    ("5 Kg Sherif", 8000, 55, "paket"),
    ("5 Kg Benom Rangli", 7500, 55, "paket"),
    ("5 Kg Benom Qora", 7000, 60, "paket"),
    ("3 Kg Eko", 5500, 100, "paket"),
    ("3 Kg Toshkent", 5500, 100, "paket"),
    ("3 Kg Anor", 5000, 33, "paket"),
    ("3 Kg Vip Qora", 5500, 80, "paket"),
    ("3 Kg Vip Rangli", 5500, 60, "paket"),
    ("3 Kg Big Bag", 5000, 45, "paket"),

    # rulonlar
    ("1 Kg Imron Rulon", 25000, 0, "rulon-paket"),
    ("1 Kg Kafolat Rulon", 25000, 0, "rulon-paket"),
    ("900 Gr Kafolat Rulon", 23000, 0, "rulon-paket"),
    ("800 Gr Kafolat Rulon", 20000, 0, "rulon-paket"),
    ("650 Gr 21 Lik Kafolat Rulon", 17000, 0, "rulon-paket"),
    ("600 Gr Eko Rulon", 17000, 0, "rulon-paket"),
    ("26 Lik Yarkiy Rulon", 13000, 0, "rulon-paket"),
    ("26 Lik Xira Rulon", 10000, 0, "rulon-paket"),
    ("21 Lik Yarkiy Rulon", 13000, 0, "rulon-paket"),
    ("21 Lik Eko Rulon", 11000, 0, "rulon-paket"),
    ("21 Lik Kafolat Rulon", 10000, 0, "rulon-paket"),
    ("18 Lik Eko Rulon", 11000, 0, "rulon-paket"),
    ("18 Lik Kafolat Rulon", 11000, 0, "rulon-paket"),
    ("15 Lik Atlash Ruloncha", 10000, 0, "rulon-paket"),

    # skotch paketlar → paket kategoriyasiga o‘tkazildi
    ("10x15 Skoch Paket", 5000, 0, "skotch-paket"),
    ("12x17 Skoch Paket", 5000, 0, "skotch-paket"),
    ("16x24 Skoch Paket", 7000, 0, "skotch-paket"),
    ("20x30 Skoch Paket", 10000, 0, "skotch-paket"),
    ("25x40 Skoch Paket", 13000, 0, "skotch-paket"),
]


async def seed_products():
    async with SessionLocal() as session:
        for name, price, stock, category in DATA:
            product = Product(
                name=name,
                category=category,
                unit="dona",
                sell_price=Decimal(price),
                cost_price=None,
                stock_quantity=Decimal(stock),
            )
            session.add(product)

        await session.commit()
        print("✅ Mahsulotlar muvaffaqiyatli qo‘shildi!")


if __name__ == "__main__":
    asyncio.run(seed_products())