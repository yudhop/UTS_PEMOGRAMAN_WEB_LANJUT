from typing import Optional

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..constants import SENSOR_TYPES
from ..extensions import db
from .base import TimestampMixin, sql_in


class Sensor(TimestampMixin, db.Model):
    """Sensor yang terpasang pada sebuah perangkat (mis. suhu, kelembapan)."""

    __tablename__ = "sensors"
    __table_args__ = (
        UniqueConstraint("device_id", "name", name="uq_sensors_device_id_name"),
        CheckConstraint(sql_in("sensor_type", SENSOR_TYPES), name="type_valid"),
        CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value < max_value",
            name="range_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    # Batas fisik sensor; pembacaan di luar rentang ditolak sebagai data tidak valid
    min_value: Mapped[Optional[float]] = mapped_column(Float)
    max_value: Mapped[Optional[float]] = mapped_column(Float)

    device = relationship("Device", back_populates="sensors")
    readings = relationship(
        "TelemetryReading",
        back_populates="sensor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alert_rules = relationship(
        "AlertRule",
        back_populates="sensor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
