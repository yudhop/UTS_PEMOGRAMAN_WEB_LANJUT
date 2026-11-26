from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..constants import DEVICE_STATUSES, DEVICE_TYPES
from ..extensions import db
from .base import TimestampMixin, sql_in


class Device(TimestampMixin, db.Model):
    """Perangkat IoT fisik (mikrokontroler / gateway) milik seorang user."""

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(sql_in("status", DEVICE_STATUSES), name="status_valid"),
        CheckConstraint(sql_in("device_type", DEVICE_TYPES), name="type_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: user yang masih punya perangkat tidak boleh dihapus
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String(30), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    firmware_version: Mapped[Optional[str]] = mapped_column(String(30))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    owner = relationship("User", back_populates="devices")
    sensors = relationship(
        "Sensor",
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
