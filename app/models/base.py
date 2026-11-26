"""Mixin & helper umum untuk model."""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow():
    """Waktu UTC "naive" (tanpa tzinfo); seluruh API menyimpan & menampilkan UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sql_in(column, values):
    """Teks CHECK constraint: kolom IN ('a','b',...)."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
