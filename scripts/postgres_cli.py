#!/usr/bin/env python3
"""Run PostgreSQL backup/restore commands from the production .env safely."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _setting(name: str, env_file: dict[str, str], default: str = "") -> str:
    return os.environ.get(name) or env_file.get(name) or default


def _connection(project_dir: Path) -> tuple[str, str, str, str, str]:
    env_file = _read_env_file(project_dir / ".env")
    database_url = _setting("DATABASE_URL_SYNC", env_file)
    if database_url:
        normalized_url = re.sub(
            r"^postgresql\+[^:]+://",
            "postgresql://",
            database_url,
            count=1,
        )
        parsed = urlsplit(normalized_url)
        return (
            parsed.hostname or "127.0.0.1",
            str(parsed.port or 5432),
            unquote(parsed.username or ""),
            unquote(parsed.password or ""),
            unquote(parsed.path.lstrip("/")),
        )

    return (
        _setting("PGHOST", env_file, "127.0.0.1"),
        _setting("PGPORT", env_file, "5432"),
        _setting("POSTGRES_USER", env_file, "adcraft"),
        _setting("POSTGRES_PASSWORD", env_file, "adcraft_dev_password"),
        _setting("POSTGRES_DB", env_file, "adcraft_erp"),
    )


def _run(command: str, file_path: Path, project_dir: Path) -> None:
    host, port, user, password, database = _connection(project_dir)
    environment = os.environ.copy()
    environment["PGPASSWORD"] = password

    if command == "dump":
        arguments = [
            "pg_dump",
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            database,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-f",
            str(file_path),
        ]
    else:
        arguments = [
            "psql",
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            database,
            "-f",
            str(file_path),
        ]

    subprocess.run(arguments, check=True, env=environment)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("dump", "restore"))
    parser.add_argument("--file", required=True, type=Path)
    args = parser.parse_args()

    default_project_dir = Path(__file__).resolve().parent.parent
    project_dir = Path(os.environ.get("PROJECT_DIR", default_project_dir))
    _run(args.command, args.file, project_dir)


if __name__ == "__main__":
    main()
