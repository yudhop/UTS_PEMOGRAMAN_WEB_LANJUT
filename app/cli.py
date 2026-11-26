"""Perintah CLI: `flask seed`."""
import click
from sqlalchemy.exc import OperationalError


def register_cli(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Hapus semua data lalu isi ulang.")
    def seed_command(reset):
        """Isi database dengan data simulasi IoT (jalankan `flask db upgrade` dulu)."""
        from seeds.seed import run_seed

        try:
            summary = run_seed(reset=reset)
        except OperationalError as exc:
            raise click.ClickException(
                "Tabel belum ada. Jalankan `flask db upgrade` terlebih dahulu."
            ) from exc

        if summary is None:
            click.echo("Database sudah berisi data. Pakai `flask seed --reset` untuk mengisi ulang.")
            return
        click.echo("Seed selesai: " + ", ".join(f"{k}={v}" for k, v in summary.items()))
