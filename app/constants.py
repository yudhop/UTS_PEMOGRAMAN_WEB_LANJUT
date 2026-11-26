"""Konstanta domain IoT monitoring (dipakai oleh model dan schema)."""

API_PREFIX = "/api/v1"
API_VERSION = "1.0.0"

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

USER_ROLES = ("admin", "operator", "viewer")

DEVICE_TYPES = ("esp32", "esp8266", "raspberry_pi", "gateway", "other")
DEVICE_STATUSES = ("active", "inactive", "maintenance")

SENSOR_TYPES = (
    "temperature",
    "humidity",
    "pressure",
    "light",
    "gas",
    "motion",
    "voltage",
    "other",
)

# operator aturan alert -> simbol yang tampil di pesan alert
RULE_OPERATORS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
SEVERITIES = ("low", "medium", "high", "critical")

ALERT_STATUSES = ("open", "acknowledged", "resolved")
# transisi status alert yang diperbolehkan
ALERT_TRANSITIONS = {
    "open": {"acknowledged", "resolved"},
    "acknowledged": {"resolved"},
    "resolved": set(),
}
# alert dengan status ini dianggap "aktif" (belum selesai ditangani)
ALERT_ACTIVE_STATUSES = ("open", "acknowledged")

# toleransi selisih jam perangkat (menit) untuk recorded_at di masa depan
FUTURE_TOLERANCE_MINUTES = 5
