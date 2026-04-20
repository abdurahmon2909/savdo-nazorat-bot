import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import settings
from app.db import init_db, sessionmaker
from app.handlers import setup_routers
from app.services.reminder import reminder_loop

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(setup_routers())

    # 🔥 REMINDER START
    asyncio.create_task(reminder_loop(bot, sessionmaker))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())