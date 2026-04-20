from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.admin_panel_inline import (
    admin_back_home_keyboard,
    admin_customers_keyboard,
    admin_main_keyboard,
    admin_products_keyboard,
)
from app.services.customers import get_customer_by_id, list_customers
from app.services.orders import list_debtor_orders, list_overdue_orders, list_recent_orders
from app.services.products import list_products
from app.services.reports import (
    get_current_year_month,
    get_monthly_report,
    get_monthly_top_products,
)

router = Router()


def is_admin(obj) -> bool:
    return bool(obj.from_user and obj.from_user.id in settings.admin_ids)


def fmt(x) -> str:
    t = format(Decimal(str(x)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


@router.message(F.text == "🔄 Admin panelni ochish")
async def open_admin_panel_message(message: Message) -> None:
    if not is_admin(message):
        return

    await message.answer(
        "Admin panel:",
        reply_markup=admin_main_keyboard(),
    )


@router.callback_query(F.data == "admin_menu:home")
async def admin_home(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            "Admin panel:",
            reply_markup=admin_main_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:products")
async def admin_products_menu(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            "Mahsulotlar bo'limi:",
            reply_markup=admin_products_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:customers")
async def admin_customers_menu(callback: CallbackQuery) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            "Mijozlar bo'limi:",
            reply_markup=admin_customers_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:requests")
async def admin_requests_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    from app.services.order_requests import list_pending_order_requests

    requests = await list_pending_order_requests(session, limit=30)
    if not requests:
        if callback.message:
            await callback.message.edit_text(
                "Hozircha kutilayotgan buyurtma so'rovlari yo'q.",
                reply_markup=admin_back_home_keyboard(),
            )
        await callback.answer()
        return

    lines = ["Kutilayotgan buyurtma so'rovlari:\n"]
    for req in requests:
        customer = await get_customer_by_id(session, int(req.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"

        lines.append(
            f"So'rov ID: {req.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Jami: {fmt(req.total_amount)} so'm\n"
            f"To'lov turi: {req.payment_type}\n"
            f"Holat: {req.status}\n"
        )

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:debtors")
async def admin_debtors_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    orders = await list_debtor_orders(session, limit=50)

    if not orders:
        if callback.message:
            await callback.message.edit_text(
                "Hozircha qarzdorlar mavjud emas.",
                reply_markup=admin_back_home_keyboard(),
            )
        await callback.answer()
        return

    lines = ["📉 Qarzdor buyurtmalar:\n"]
    total_debt = Decimal("0")

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"

        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        total_debt += left

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Qoldiq: {fmt(left)} so'm\n"
            f"Holat: {order.status}\n"
        )

    lines.append(f"Umumiy qarz: {fmt(total_debt)} so'm")

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:history")
async def admin_history_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    orders = await list_recent_orders(session, limit=50)
    if not orders:
        if callback.message:
            await callback.message.edit_text(
                "Hozircha buyurtmalar mavjud emas.",
                reply_markup=admin_back_home_keyboard(),
            )
        await callback.answer()
        return

    lines = ["📚 So'nggi buyurtmalar:\n"]
    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        name = customer.full_name if customer else "Noma'lum"

        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid

        lines.append(
            f"ID: {order.id}\n"
            f"Mijoz: {name}\n"
            f"Jami: {fmt(total)} so'm\n"
            f"To'langan: {fmt(paid)} so'm\n"
            f"Qoldiq: {fmt(left)} so'm\n"
            f"Holat: {order.status}\n"
        )

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:reports")
async def admin_reports_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    year, month = get_current_year_month()
    report = await get_monthly_report(session, year, month)
    top_products = await get_monthly_top_products(session, year, month, limit=5)

    lines = [
        f"{month}-{year} hisobot:\n",
        f"Buyurtmalar soni: {report['order_count']}",
        f"Jami savdo: {fmt(report['total'])} so'm",
        f"To'langan: {fmt(report['paid'])} so'm",
        f"Qarz: {fmt(report['unpaid'])} so'm",
        "",
        "Tez sotilayotgan mahsulotlar:",
    ]

    if top_products:
        for index, item in enumerate(top_products, start=1):
            lines.append(f"{index}. {item['name']} — {fmt(item['sold_qty'])} dona")
    else:
        lines.append("Hozircha sotuv statistikasi yo'q.")

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:overdue")
async def admin_overdue_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    orders = await list_overdue_orders(session, days=7, limit=50)

    if not orders:
        if callback.message:
            await callback.message.edit_text(
                "Kechikkan qarzlar yo'q.",
                reply_markup=admin_back_home_keyboard(),
            )
        await callback.answer()
        return

    from datetime import datetime

    lines = ["⏰ 7 kundan oshgan qarzlar:\n"]

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        name = customer.full_name if customer else "Noma'lum"

        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        days = (datetime.utcnow() - order.created_at).days

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Mijoz: {name}\n"
            f"Qoldiq: {fmt(left)} so'm\n"
            f"Kechikish: {days} kun\n"
        )

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_menu:stock")
async def admin_stock_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    products = await list_products(session, limit=30)
    if not products:
        if callback.message:
            await callback.message.edit_text(
                "Mahsulotlar yo'q.",
                reply_markup=admin_back_home_keyboard(),
            )
        await callback.answer()
        return

    lines = ["🧮 Qoldiq holati:\n"]
    for p in products:
        lines.append(
            f"ID: {p.id}\n"
            f"Nomi: {p.name}\n"
            f"Qoldiq: {fmt(p.stock_quantity)} {p.unit}\n"
        )

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer()