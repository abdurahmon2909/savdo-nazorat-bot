from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_or_update_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    username: str | None,
    phone: str | None,
    role: str = "mijoz",
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)

    if user is None:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone=phone,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    user.full_name = full_name
    user.username = username
    if phone:
        user.phone = phone
    user.role = role

    await session.commit()
    await session.refresh(user)
    return user