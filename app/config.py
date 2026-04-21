import os
from decimal import Decimal


class Settings:
    def __init__(self) -> None:
        self.bot_token: str = os.getenv("BOT_TOKEN", "").strip()
        raw_db_url = os.getenv("DATABASE_URL", "").strip()
        raw_admin_ids = os.getenv("ADMIN_IDS", "").strip()
        self.low_stock_threshold = Decimal(os.getenv("LOW_STOCK_THRESHOLD", "5"))

        if not self.bot_token:
            raise ValueError("BOT_TOKEN topilmadi. Railway Variables ichiga qo'shing.")

        if not raw_db_url:
            raise ValueError("DATABASE_URL topilmadi. Railway Variables ichiga qo'shing.")

        if raw_db_url.startswith("postgresql://"):
            raw_db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)

        self.database_url: str = raw_db_url

        self.admin_ids: list[int] = []
        if raw_admin_ids:
            self.admin_ids = [
                int(item.strip())
                for item in raw_admin_ids.split(",")
                if item.strip().isdigit()
            ]


settings = Settings()