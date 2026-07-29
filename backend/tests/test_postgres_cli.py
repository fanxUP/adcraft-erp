from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "postgres_cli.py"
SPEC = spec_from_file_location("postgres_cli", SCRIPT_PATH)
assert SPEC and SPEC.loader
postgres_cli = module_from_spec(SPEC)
SPEC.loader.exec_module(postgres_cli)


def test_read_env_file_keeps_unquoted_values_with_spaces(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "APP_NAME=AdCraft ERP\n"
        "DATABASE_URL_SYNC='postgresql+psycopg2://user:pass@db:5432/app'\n",
        encoding="utf-8",
    )

    values = postgres_cli._read_env_file(env_path)

    assert values["APP_NAME"] == "AdCraft ERP"
    assert values["DATABASE_URL_SYNC"].endswith("/app")


def test_connection_uses_database_url_and_decodes_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL_SYNC", raising=False)
    (tmp_path / ".env").write_text(
        "DATABASE_URL_SYNC=postgresql+psycopg2://ad%40min:p%40ss@db.local:5544/adcraft_erp\n",
        encoding="utf-8",
    )

    connection = postgres_cli._connection(tmp_path)

    assert connection == ("db.local", "5544", "ad@min", "p@ss", "adcraft_erp")


def test_dump_passes_password_through_environment(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "DATABASE_URL_SYNC=postgresql+psycopg2://adcraft:secret@127.0.0.1:5432/adcraft_erp\n",
        encoding="utf-8",
    )
    calls = []

    def fake_run(arguments, *, check, env):
        calls.append((arguments, check, env))

    monkeypatch.setattr(postgres_cli.subprocess, "run", fake_run)
    output = tmp_path / "backup.sql"

    postgres_cli._run("dump", output, tmp_path)

    arguments, check, environment = calls[0]
    assert arguments[0] == "pg_dump"
    assert arguments[-1] == str(output)
    assert check is True
    assert environment["PGPASSWORD"] == "secret"
    assert "secret" not in arguments
