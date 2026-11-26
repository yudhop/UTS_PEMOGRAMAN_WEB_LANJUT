"""Endpoint informasi dan health check."""
from flask import Blueprint
from sqlalchemy import text

from ..constants import API_PREFIX, API_VERSION
from ..extensions import db
from ..utils.errors import ApiError
from ..utils.responses import success

bp = Blueprint("health", __name__)


@bp.get("/")
def index():
    return success(
        {
            "name": "IoT Monitor API",
            "version": API_VERSION,
            "base_url": API_PREFIX,
            "health": f"{API_PREFIX}/health",
        }
    )


@bp.get(f"{API_PREFIX}/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - detail DB tidak boleh bocor
        raise ApiError(503, "SERVICE_UNAVAILABLE", "Database is unavailable.") from exc
    return success({"status": "ok", "database": "ok", "version": API_VERSION})
