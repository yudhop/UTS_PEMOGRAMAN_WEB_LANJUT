from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from ..constants import USER_ROLES
from ..extensions import db
from .base import TimestampMixin, sql_in


class User(TimestampMixin, db.Model):
    """Aktor sistem: admin, operator (pemilik perangkat), atau viewer."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint(sql_in("role", USER_ROLES), name="role_valid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="operator")

    devices = relationship("Device", back_populates="owner")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)
