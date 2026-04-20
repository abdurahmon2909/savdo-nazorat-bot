import os


class Settings:
    def __init__(self) -> None:
        self.bot_token: str = os.getenv("BOT_TOKEN", "").strip()
        raw_db_url = os.getenv("DATABASE_URL", "").strip()

        if not self.bot_token:
            raise ValueError("BOT_TOKEN topilmadi. Railway Variables ichiga qo'shing.")

        if not raw_db_url:
            raise ValueError("DATABASE_URL topilmadi. Railway Variables ichiga qo'shing.")

        if raw_db_url.startswith("postgresql://"):
            raw_db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)

        self.database_url: str = raw_db_url


settings = Settings()