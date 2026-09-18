"""Shared SQLAlchemy model infrastructure."""

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp for application-managed fields."""

    return datetime.now(timezone.utc)
