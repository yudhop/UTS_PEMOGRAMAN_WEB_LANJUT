from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .base import utcnow


class TelemetryReading(db.Model):
    """Satu pembacaan nilai sensor pada waktu tertentu (data time-series)."""

    __tablename__ = "telemetry_readings"
    __table_args__ = (Index("ix_telemetry_sensor_recorded", "sensor_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    sensor = relationship("Sensor", back_populates="readings")
