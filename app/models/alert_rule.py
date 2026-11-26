from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..constants import RULE_OPERATORS, SEVERITIES
from ..extensions import db
from .base import TimestampMixin, sql_in


class AlertRule(TimestampMixin, db.Model):
    """Aturan ambang batas: jika value <operator> threshold maka buat alert."""

    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint(sql_in("operator", tuple(RULE_OPERATORS)), name="operator_valid"),
        CheckConstraint(sql_in("severity", SEVERITIES), name="severity_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(5), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sensor = relationship("Sensor", back_populates="alert_rules")
    alerts = relationship(
        "Alert",
        back_populates="rule",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
