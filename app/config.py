"""Konfigurasi aplikasi (Development / Testing / Production)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Nilai yang sudah ada di environment tidak ditimpa oleh .env
load_dotenv(BASE_DIR / ".env")

DEFAULT_SECRET_KEY = "dev-only-change-me"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    # Path SQLite relatif disimpan di folder instance/
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///iot_monitor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # batasi body request maksimal 1 MB
    API_KEY = os.getenv("API_KEY", "")  # kosong = proteksi tulis dimatikan
    DEBUG = False
    TESTING = False

    @classmethod
    def init_app(cls, app):
        """Hook validasi tambahan saat app dibuat."""


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    API_KEY = ""


class ProductionConfig(Config):
    @classmethod
    def init_app(cls, app):
        if app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY harus diisi dengan nilai acak saat APP_ENV=production."
            )


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = (name or os.getenv("APP_ENV", "development")).lower()
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(
            f"APP_ENV '{name}' tidak dikenal. Pilih: {', '.join(CONFIGS)}"
        ) from None
