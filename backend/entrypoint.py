#!/usr/bin/env python3
"""
AdCraft ERP — Windows Entry Point (PyInstaller bootstrap).

This script replaces the Docker CMD for Windows deployments.
When packaged by PyInstaller (--onedir), it:
  1. Resolves all paths relative to the executable location
  2. Loads and patches .env with runtime paths
  3. Runs Alembic migrations
  4. Seeds default roles and admin user (idempotent)
  5. Starts uvicorn on 0.0.0.0:8000

Usage:
  backend.exe              Normal start (production)
  backend.exe --init       Force re-initialization
  backend.exe --port 8080  Custom port
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution (PyInstaller-aware)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle (--onedir)
    EXE_DIR = Path(sys.executable).parent.resolve()
    INTERNAL_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    # Running from source (development)
    EXE_DIR = Path(__file__).resolve().parent
    INTERNAL_DIR = EXE_DIR

os.chdir(str(EXE_DIR))


def _patch_config():
    """Set environment variables so that app.core.config picks up runtime paths."""
    # Uploads & logs directories — relative to the exe, not Docker's /app
    uploads_dir = EXE_DIR / "uploads"
    logs_dir = EXE_DIR / "logs"
    uploads_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    os.environ.setdefault("LOCAL_UPLOAD_DIR", str(uploads_dir))
    os.environ.setdefault("FRONTEND_DIR", str(EXE_DIR / "frontend"))

    # Ensure a .env exists
    env_file = EXE_DIR / ".env"
    if not env_file.exists():
        _generate_env(env_file)

    # Override DATABASE_URL to use local PostgreSQL (relative paths)
    _apply_db_defaults()


def _generate_env(env_file: Path):
    """Create a minimal .env with a random SECRET_KEY."""
    import secrets

    secret = secrets.token_hex(32)
    env_file.write_text(
        f"# AdCraft ERP — auto-generated configuration\n"
        f"APP_NAME=AdCraft ERP\n"
        f"APP_ENV=production\n"
        f"SECRET_KEY={secret}\n"
        f"DATABASE_URL=postgresql+asyncpg://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp\n"
        f"DATABASE_URL_SYNC=postgresql+psycopg2://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp\n"
        f"REDIS_URL=\n"
        f"UPLOAD_STORAGE=local\n"
        f"LOCAL_UPLOAD_DIR={EXE_DIR / 'uploads'}\n"
        f"JWT_EXPIRE_MINUTES=1440\n"
        f"AI_ENABLED=false\n"
    )
    print(f"✅ Generated .env with random SECRET_KEY: {env_file}")


def _apply_db_defaults():
    """Set default DATABASE_URL if not configured."""
    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = (
            "postgresql+asyncpg://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp"
        )
    if not os.environ.get("DATABASE_URL_SYNC"):
        os.environ["DATABASE_URL_SYNC"] = (
            "postgresql+psycopg2://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp"
        )


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------
def _run_alembic():
    """Run Alembic migrations."""
    alembic_dir = INTERNAL_DIR / "alembic"
    if not alembic_dir.exists():
        print("⚠  Alembic directory not found — skipping migrations")
        return

    print("🔄 Running database migrations...")
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command

        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option("script_location", str(alembic_dir))
        # Use sync URL for alembic
        sync_url = os.environ.get(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg2://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp",
        )
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations complete")
    except Exception as exc:
        print(f"⚠  Migration warning: {exc}")


def _seed_data():
    """Run init_app.py to seed roles, permissions, and admin user."""
    init_script = INTERNAL_DIR / "scripts" / "init_app.py"
    if not init_script.exists():
        print("⚠  Seed script not found — skipping data initialization")
        return

    print("🌱 Seeding initial data...")
    try:
        # Run the init script in-process
        import importlib.util
        spec = importlib.util.spec_from_file_location("init_app", str(init_script))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["init_app"] = module
            spec.loader.exec_module(module)
            import asyncio
            asyncio.run(module.main())
        print("✅ Seed data complete")
    except Exception as exc:
        print(f"⚠  Seed data warning: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _patch_config()

    # Handle CLI flags
    force_init = "--init" in sys.argv
    port = 8000
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    if force_init:
        print("🔧 Force-init mode")
        _run_alembic()
        _seed_data()
        print("✅ Initialization complete — restart without --init to run normally")
        return

    # Always run migrations on startup (safe — idempotent)
    _run_alembic()
    _seed_data()

    # Start uvicorn
    print(f"\n🚀 Starting AdCraft ERP on http://127.0.0.1:{port}")
    print(f"   API docs: http://127.0.0.1:{port}/api/docs")
    print(f"   Frontend: http://127.0.0.1:{port}/")
    print("   Press Ctrl+C to stop\n")

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
