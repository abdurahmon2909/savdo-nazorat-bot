from aiogram import Router

from app.handlers.admin_customers import router as admin_customers_router
from app.handlers.admin_debtors import router as admin_debtors_router
from app.handlers.admin_history import router as admin_history_router
from app.handlers.admin_order_inline import router as admin_order_inline_router
from app.handlers.admin_order_requests import router as admin_order_requests_router
from app.handlers.admin_orders import router as admin_orders_router
from app.handlers.admin_overdue import router as admin_overdue_router
from app.handlers.admin_payments import router as admin_payments_router
from app.handlers.admin_products import router as admin_products_router
from app.handlers.admin_reports import router as admin_reports_router
from app.handlers.admin_stock import router as admin_stock_router
from app.handlers.customer_catalog import router as customer_catalog_router
from app.handlers.start import router as start_router


def setup_routers() -> Router:
    r = Router()

    r.include_router(start_router)
    r.include_router(admin_customers_router)
    r.include_router(admin_products_router)
    r.include_router(admin_orders_router)
    r.include_router(admin_order_requests_router)
    r.include_router(admin_order_inline_router)
    r.include_router(admin_payments_router)
    r.include_router(admin_debtors_router)
    r.include_router(admin_history_router)
    r.include_router(admin_stock_router)
    r.include_router(admin_reports_router)
    r.include_router(admin_overdue_router)
    r.include_router(customer_catalog_router)

    return r