import os
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


def safe_upload_name(original_name: str | None, prefix: str) -> tuple[str, str]:
    """Return a storage name and the display name without accepting path components."""
    display_name = Path(original_name or "attachment").name
    display_name = re.sub(r"[\x00-\x1f\x7f]", "", display_name).strip() or "attachment"
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(display_name).stem)[:100] or "attachment"
    suffix = re.sub(r"[^A-Za-z0-9.]", "", Path(display_name).suffix)[:16]
    return f"{prefix}_{stem}{suffix}", display_name


def confined_path(root: str, relative_path: str) -> str:
    root_path = Path(root).resolve()
    candidate = (root_path / relative_path).resolve()
    if candidate != root_path and root_path not in candidate.parents:
        raise HTTPException(status_code=400, detail="非法文件路径")
    return str(candidate)


async def save_upload(file: UploadFile, destination: str) -> None:
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    total = 0
    try:
        with open(destination, "wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ATTACHMENT_SIZE:
                    raise HTTPException(status_code=413, detail="附件大小不能超过20MB")
                output.write(chunk)
    except Exception:
        if os.path.exists(destination):
            os.remove(destination)
        raise
