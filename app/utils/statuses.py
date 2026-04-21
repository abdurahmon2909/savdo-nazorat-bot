def uzbek_order_status(status: str | None) -> str:
    mapping = {
        "pending": "Kutilmoqda",
        "approved": "Tasdiqlangan",
        "rejected": "Rad etilgan",
        "cancelled": "Bekor qilingan",
        "draft": "Qoralama",
        "unpaid": "To'lanmagan",
        "partial": "Qisman to'langan",
        "paid": "To'langan",
        "overdue": "Kechikkan",
    }
    if not status:
        return "Noma'lum"
    return mapping.get(str(status).lower(), str(status))