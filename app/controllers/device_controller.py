"""Endpoint /devices: registrasi dan pengelolaan perangkat IoT."""
from flask import Blueprint, request
from sqlalchemy import or_, select

from ..constants import API_PREFIX
from ..extensions import db
from ..models import Device, User
from ..schemas.device_schema import DeviceQuerySchema, DeviceSchema
from ..utils.pagination import apply_sorting, contains, paginate
from ..utils.responses import created, no_content, success
from ..utils.validation import (
    ensure_unique,
    get_or_404,
    load_args,
    load_json,
    require_reference,
)

bp = Blueprint("devices", __name__, url_prefix=f"{API_PREFIX}/devices")
device_schema = DeviceSchema()

SORTABLE = {
    "name": Device.name,
    "serial_number": Device.serial_number,
    "status": Device.status,
    "last_seen_at": Device.last_seen_at,
    "created_at": Device.created_at,
}


@bp.post("")
def create_device():
    data = load_json(device_schema)
    require_reference(User, data["owner_id"], "owner_id")
    ensure_unique(Device, "serial_number", data["serial_number"])

    device = Device(**data)
    db.session.add(device)
    db.session.commit()
    return created(device_schema.dump(device), "devices.get_device", device_id=device.id)


@bp.get("")
def list_devices():
    args = load_args(DeviceQuerySchema())
    stmt = select(Device)
    if "q" in args:
        stmt = stmt.where(
            or_(contains(Device.name, args["q"]), contains(Device.serial_number, args["q"]))
        )
    for field in ("status", "device_type", "owner_id"):
        if field in args:
            stmt = stmt.where(getattr(Device, field) == args[field])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "-created_at", Device.id)
    data, meta = paginate(stmt, device_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:device_id>")
def get_device(device_id):
    return success(device_schema.dump(get_or_404(Device, device_id)))


@bp.route("/<int:device_id>", methods=["PUT", "PATCH"])
def update_device(device_id):
    """PUT = ganti seluruh field; PATCH = ubah sebagian field."""
    device = get_or_404(Device, device_id)
    data = load_json(device_schema, partial=request.method == "PATCH")
    if "owner_id" in data:
        require_reference(User, data["owner_id"], "owner_id")
    if "serial_number" in data:
        ensure_unique(Device, "serial_number", data["serial_number"], exclude_id=device.id)

    for field, value in data.items():
        setattr(device, field, value)
    db.session.commit()
    return success(device_schema.dump(device))


@bp.delete("/<int:device_id>")
def delete_device(device_id):
    device = get_or_404(Device, device_id)
    db.session.delete(device)  # sensor, telemetri, rule, dan alert ikut terhapus (CASCADE)
    db.session.commit()
    return no_content()
