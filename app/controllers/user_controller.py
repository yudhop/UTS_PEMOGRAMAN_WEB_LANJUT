"""Endpoint /users: pendaftaran dan pengelolaan akun."""
from flask import Blueprint
from sqlalchemy import func, or_, select

from ..constants import API_PREFIX
from ..extensions import db
from ..models import Device, User
from ..schemas.user_schema import UserQuerySchema, UserSchema
from ..utils.errors import ApiError
from ..utils.pagination import apply_sorting, contains, paginate
from ..utils.responses import created, no_content, success
from ..utils.validation import ensure_unique, get_or_404, load_args, load_json

bp = Blueprint("users", __name__, url_prefix=f"{API_PREFIX}/users")
user_schema = UserSchema()

SORTABLE = {
    "username": User.username,
    "email": User.email,
    "created_at": User.created_at,
}


@bp.post("")
def create_user():
    data = load_json(user_schema)
    ensure_unique(User, "username", data["username"])
    ensure_unique(User, "email", data["email"])

    user = User(username=data["username"], email=data["email"], role=data["role"])
    user.set_password(data["password"])  # simpan hash, bukan password asli
    db.session.add(user)
    db.session.commit()
    return created(user_schema.dump(user), "users.get_user", user_id=user.id)


@bp.get("")
def list_users():
    args = load_args(UserQuerySchema())
    stmt = select(User)
    if "q" in args:
        stmt = stmt.where(
            or_(contains(User.username, args["q"]), contains(User.email, args["q"]))
        )
    if "role" in args:
        stmt = stmt.where(User.role == args["role"])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "-created_at", User.id)
    data, meta = paginate(stmt, user_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:user_id>")
def get_user(user_id):
    return success(user_schema.dump(get_or_404(User, user_id)))


@bp.delete("/<int:user_id>")
def delete_user(user_id):
    user = get_or_404(User, user_id)
    device_count = db.session.scalar(
        select(func.count(Device.id)).where(Device.owner_id == user.id)
    )
    if device_count:
        raise ApiError(
            409,
            "CONFLICT",
            f"User still owns {device_count} device(s); reassign or delete them first.",
        )
    db.session.delete(user)
    db.session.commit()
    return no_content()
