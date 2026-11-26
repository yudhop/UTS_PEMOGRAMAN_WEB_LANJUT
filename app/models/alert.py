from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..constants import ALERT_STATUSES, SEVERITIES
from ..extensions import db
from .base import sql_in, utcnow


class Alert(db.Model):
    """Kejadian alert yang dihasilkan ketika sebuah pembacaan melanggar aturan."""

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(sql_in("status", ALERT_STATUSES), name="status_valid"),
        CheckConstraint(sql_in("severity", SEVERITIES), name="severity_valid"),
        Index("ix_alerts_status_triggered", "status", "triggered_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SET NULL: alert tetap menjadi catatan walau pembacaan asalnya dihapus
    reading_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("telemetry_readings.id", ondelete="SET NULL")
    )
    acknowledged_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    rule = relationship("AlertRule", back_populates="alerts")
    reading = relationship("TelemetryReading")
    acknowledged_by = relationship("User")
