"""Backup management API endpoints.

Provides endpoints to create, list, and restore backups.
Designed for admin users only.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Body, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, engine
from app.core.deps import get_current_user
from app.core.permissions import require_permission, PERM_BACKUP_CREATE, PERM_BACKUP_READ, PERM_BACKUP_RESTORE, PERM_BACKUP_DELETE
from app.models.user import User
from app.schemas.common import success, error

router = APIRouter(prefix="/admin/backup", tags=["Admin"])

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKUP_DIR = PROJECT_DIR / "backups"
SCRIPTS_DIR = PROJECT_DIR / "scripts"
BACKUP_SCRIPT = SCRIPTS_DIR / "backup.sh"
RESTORE_SCRIPT = SCRIPTS_DIR / "restore.sh"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _get_backups() -> list[dict]:
    """List backup files sorted by creation time (newest first)."""
    if not BACKUP_DIR.exists():
        return []

    backups: list[dict] = []
    for f in sorted(BACKUP_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name.endswith(".tar.gz") and f.name.startswith("backup_"):
            stat = f.stat()
            # Parse timestamp from filename: backup_20260629_020000.tar.gz
            ts_str = f.name.replace("backup_", "").replace(".tar.gz", "")
            created_at = None
            try:
                created_at = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").isoformat()
            except ValueError:
                created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

            backups.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "created_at": created_at,
            })
    return backups


@router.post("/create")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_BACKUP_CREATE)),
):
    """Create a full backup (database + uploads)."""
    if not BACKUP_SCRIPT.exists():
        return error(50001, f"备份脚本不存在: {BACKUP_SCRIPT}")

    try:
        result = subprocess.run(
            ["bash", str(BACKUP_SCRIPT)],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        if result.returncode != 0:
            return error(50002, f"备份失败: {result.stderr.strip() or result.stdout.strip()}")

        # Find the newly created backup file
        backups = _get_backups()
        latest = backups[0] if backups else None

        return success({
            "message": "备份完成",
            "output": result.stdout.strip(),
            "backup": latest,
        })
    except subprocess.TimeoutExpired:
        return error(50003, "备份超时（超过5分钟）")
    except Exception as e:
        logger.exception("Backup creation failed: %s", e)
        return error(50004, f"备份过程出错: {str(e)}")


@router.get("/list")
async def list_backups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_BACKUP_READ)),
):
    """List all available backup files."""
    backups = _get_backups()
    total_size = sum(b["size"] for b in backups)
    return success({
        "backups": backups,
        "total": len(backups),
        "total_size": total_size,
        "total_size_display": _format_size(total_size),
    })


@router.post("/restore")
async def restore_backup(
    filename: str = Body(..., embed=True),
    current_user: User = Depends(require_permission(PERM_BACKUP_RESTORE)),
):
    """Restore from a specific backup file.

    WARNING: This will overwrite the current database and uploads.
    The restore script runs non-interactively from the API (no confirmation prompt).
    No db session is opened — the restore replaces the entire database.
    """
    if not RESTORE_SCRIPT.exists():
        return error(50001, f"恢复脚本不存在: {RESTORE_SCRIPT}")

    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        return error(40401, f"备份文件不存在: {filename}")

    try:
        # Terminate all other database connections and dispose pool BEFORE
        # restore — existing sessions hold locks that block ALTER TABLE.
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid != pg_backend_pid()"
            ))
            await conn.commit()
        await engine.dispose()
        logger.info("All DB connections terminated and pool disposed before restore")

        # Use asyncio subprocess to avoid blocking the event loop
        proc = await asyncio.create_subprocess_exec(
            "bash", str(RESTORE_SCRIPT), str(backup_path),
            cwd=str(PROJECT_DIR),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=b"yes\n"),
            timeout=600,
        )
        output = stdout.decode().strip()
        err_output = stderr.decode().strip()

        if proc.returncode != 0:
            return error(50002, f"恢复失败: {err_output or output}")

        # Dispose connection pool — old connections point to replaced database
        await engine.dispose()
        logger.info("Database connection pool disposed after restore")

        return success({
            "message": "恢复完成",
            "output": output,
        })
    except asyncio.TimeoutError:
        return error(50003, "恢复超时（超过10分钟）")
    except Exception as e:
        logger.exception("Backup restore failed: %s", e)
        return error(50004, f"恢复过程出错: {str(e)}")


@router.delete("/{filename}")
async def delete_backup(
    filename: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_BACKUP_DELETE)),
):
    """Delete a specific backup file."""
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        return error(40401, f"备份文件不存在: {filename}")

    try:
        backup_path.unlink()
        return success({"message": f"已删除备份: {filename}"})
    except Exception as e:
        logger.exception("Backup deletion failed: %s", e)
        return error(50004, f"删除失败: {str(e)}")


@router.get("/export/{filename}")
async def export_backup(
    filename: str,
    current_user: User = Depends(require_permission(PERM_BACKUP_READ)),
):
    """Download a backup file to the browser."""
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return error(40001, "非法文件名")

    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        return error(40401, f"备份文件不存在: {filename}")

    return FileResponse(
        path=str(backup_path),
        filename=filename,
        media_type="application/gzip",
    )


@router.post("/import")
async def import_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(PERM_BACKUP_CREATE)),
):
    """Upload a backup file (.tar.gz) to the server."""
    if not file.filename or not file.filename.endswith(".tar.gz"):
        return error(40001, "仅支持 .tar.gz 格式的备份文件")

    # Prevent path traversal
    safe_name = file.filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    dest = BACKUP_DIR / safe_name

    if dest.exists():
        return error(40002, f"同名备份已存在: {safe_name}")

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        dest.write_bytes(content)

        stat = dest.stat()
        ts_str = safe_name.replace("backup_", "").replace(".tar.gz", "")
        created_at = None
        try:
            created_at = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").isoformat()
        except ValueError:
            created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

        return success({
            "message": "导入完成",
            "backup": {
                "filename": safe_name,
                "size": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "created_at": created_at,
            },
        })
    except Exception as e:
        logger.exception("Backup import failed: %s", e)
        return error(50004, f"导入失败: {str(e)}")
