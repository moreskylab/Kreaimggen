"""
Database CRUD helpers – all async, all typed.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import User


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
) -> User:
    user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(user)
    await db.flush()   # assign DB-generated id before commit
    await db.refresh(user)
    return user
