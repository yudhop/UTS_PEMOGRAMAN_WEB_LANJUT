"""Pagination, sorting, dan pencarian untuk endpoint daftar."""
from marshmallow import EXCLUDE, Schema, fields, validate

from ..constants import DEFAULT_PER_PAGE, MAX_PER_PAGE
from ..extensions import db
from .errors import ApiError


class PaginationSchema(Schema):
    """Dasar query string untuk semua endpoint daftar: ?page=&per_page=&sort="""

    class Meta:
        unknown = EXCLUDE  # parameter tak dikenal diabaikan

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(
        load_default=DEFAULT_PER_PAGE, validate=validate.Range(min=1, max=MAX_PER_PAGE)
    )
    sort = fields.Str(load_default=None, validate=validate.Length(max=100))


def paginate(stmt, serializer, args):
    """Jalankan SELECT berhalaman dan kembalikan (items_serialized, meta)."""
    page = db.paginate(
        stmt,
        page=args["page"],
        per_page=args["per_page"],
        max_per_page=MAX_PER_PAGE,
        error_out=False,
    )
    meta = {
        "page": page.page,
        "per_page": page.per_page,
        "total": page.total,
        "pages": page.pages,
    }
    return serializer.dump(page.items, many=True), meta


def apply_sorting(stmt, sortable, sort, default, id_column):
    """Terapkan ?sort=field,-other. `sortable` = {nama_field: kolom}.

    Awalan '-' berarti descending. id selalu dipakai sebagai pembeda terakhir
    supaya urutan halaman stabil.
    """
    order_by = []
    for token in (sort or default).split(","):
        token = token.strip()
        if not token:
            continue
        descending = token.startswith("-")
        name = token[1:] if descending else token
        column = sortable.get(name)
        if column is None:
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "Input validation failed.",
                {"sort": [f"Unsupported sort field '{name}'. Allowed: {', '.join(sortable)}."]},
            )
        order_by.append(column.desc() if descending else column.asc())
    order_by.append(id_column.desc() if order_by and descending else id_column.asc())
    return stmt.order_by(*order_by)


def contains(column, term):
    """Pencarian substring case-insensitive; karakter wildcard LIKE di-escape."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")
