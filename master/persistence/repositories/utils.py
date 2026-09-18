"""Small value conversions shared by repository implementations."""

from datetime import datetime, timezone
import uuid


def normalize_id(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)
