from aiogram import Router

from app.handlers.admin_customers import router as admin_customers_router
from app.handlers.start import router as start_router


def setup_routers() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(admin_customers_router)
    return router