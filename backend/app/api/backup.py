"""Backup management API endpoints.

Provides endpoints to create, list, and restore backups.
Designed for admin users only.
"""

import asyncio
import logging
import re
import subprocess
import tarfile
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
BACKUP_FILENAME_RE = re.compile(r"^backup_(?P<date>\d{8})_(?P<time>\d{6})\.tar\.gz$")
MAX_BACKUP_UPLOAD_BYTES = 50 * 1024 * 1024


def _is_valid_backup_filename(filename: str) -> bool:
    """Accept only backup files produced by the backup script."""
    match = BACKUP_FILENAME_RE.fullmatch(filename)
    if not match:
        return False
    try:
        datetime.strptime(f"{match['date']}_{match['time']}", "%Y%m%d_%H%M%S")
    except ValueError:
        return False
    return True


def _safe_backup_path(filename: str) -> Path | None:
    """Resolve an existing backup without following user-controlled paths."""
    if not _is_valid_backup_filename(filename):
        return None

    backup_dir = BACKUP_DIR.resolve()
    candidate = BACKUP_DIR / filename
    if candidate.is_symlink():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return None

    if not resolved.is_file() or resolved.parent != backup_dir:
        return None
    return resolved


def _validate_backup_archive(path: Path) -> str | None:
    """Validate the archive shape before it can reach the restore script."""
    expected_sql = f"{path.name.removesuffix('.tar.gz')}.sql"
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
    except (OSError, tarfile.TarError) as exc:
        return f"备份压缩包无法读取: {exc}"

    if len(members) != 1:
        return "备份压缩包必须且只能包含一个数据库 SQL 文件"

    member = members[0]
    if member.name != expected_sql or not member.isfile() or member.issym() or member.islnk():
        return "备份压缩包内容不符合数据库备份格式"
    return None


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

    backups: list[tuple[float, dict]] = []
    for f in BACKUP_DIR.iterdir():
        if not _is_valid_backup_filename(f.name):
            continue
        safe_path = _safe_backup_path(f.name)
        if safe_path is None:
            continue
        try:
            stat = safe_path.stat()
        except OSError:
            continue

        ts_str = f.name.removeprefix("backup_").removesuffix(".tar.gz")
        backups.append((stat.st_mtime, {
            "filename": f.name,
            "size": stat.st_size,
            "size_display": _format_size(stat.st_size),
            "created_at": datetime.strptime(ts_str, "%Y%m%d_%H%M%S").isoformat(),
        }))
    return [backup for _, backup in sorted(backups, key=lambda item: item[0], reverse=True)]


@router.post("/create")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_BACKUP_CREATE)),
):
    """Create a database-only backup."""
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

    WARNING: This will overwrite the current database.
    The restore script runs non-interactively from the API (no confirmation prompt).
    No db session is opened — the restore replaces the entire database.
    """
    if not RESTORE_SCRIPT.exists():
        return error(50001, f"恢复脚本不存在: {RESTORE_SCRIPT}")

    if not _is_valid_backup_filename(filename):
        return error(40001, "非法备份文件名")
    backup_path = _safe_backup_path(filename)
    if backup_path is None:
        return error(40401, f"备份文件不存在: {filename}")
    archive_error = _validate_backup_archive(backup_path)
    if archive_error:
        return error(40002, archive_error)

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
    if not _is_valid_backup_filename(filename):
        return error(40001, "非法备份文件名")
    backup_path = _safe_backup_path(filename)
    if backup_path is None:
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
    if not _is_valid_backup_filename(filename):
        return error(40001, "非法备份文件名")
    backup_path = _safe_backup_path(filename)
    if backup_path is None:
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
    if not file.filename or not _is_valid_backup_filename(file.filename):
        return error(40001, "仅支持 backup_YYYYMMDD_HHMMSS.tar.gz 格式的备份文件")

    safe_name = file.filename
    dest = BACKUP_DIR / safe_name

    if dest.exists():
        return error(40002, f"同名备份已存在: {safe_name}")

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        total_size = 0
        with dest.open("xb") as output_file:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_BACKUP_UPLOAD_BYTES:
                    raise ValueError("备份文件超过 50 MB 限制")
                output_file.write(chunk)

        archive_error = _validate_backup_archive(dest)
        if archive_error:
            dest.unlink(missing_ok=True)
            return error(40002, archive_error)

        stat = dest.stat()
        ts_str = safe_name.removeprefix("backup_").removesuffix(".tar.gz")
        created_at = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").isoformat()

        return success({
            "message": "导入完成",
            "backup": {
                "filename": safe_name,
                "size": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "created_at": created_at,
            },
        })
    except ValueError as e:
        if dest.is_file() and not dest.is_symlink():
            dest.unlink(missing_ok=True)
        return error(40003, str(e))
    except Exception as e:
        if dest.is_file() and not dest.is_symlink():
            dest.unlink(missing_ok=True)
        logger.exception("Backup import failed: %s", e)
        return error(50004, f"导入失败: {str(e)}")
