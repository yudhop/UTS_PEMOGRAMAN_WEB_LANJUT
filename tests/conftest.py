import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    """App testing dengan SQLite in-memory yang bersih untuk setiap test."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
