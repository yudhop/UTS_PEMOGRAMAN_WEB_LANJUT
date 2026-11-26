"""Entry point: `flask run` / `python run.py` / `gunicorn run:app`."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
