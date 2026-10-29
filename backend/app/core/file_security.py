import os
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


async def read_upload(file: UploadFile, max_bytes: int = MAX_ATTACHMENT_SIZE) -> bytes:
    """Bound memory use before parsing or saving an uploaded file."""
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"文件大小不能超过{max_bytes // (1024 * 1024)}MB")
    return content


def validate_attachment_content(filename: str | None, content: bytes) -> None:
    extension = Path(filename or "").suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
               ".ppt", ".pptx", ".txt", ".csv", ".cdr", ".ai", ".eps", ".psd", ".dwg", ".dxf",
               ".zip", ".rar", ".7z", ".mp4", ".mov", ".webm"}
    if extension not in allowed:
        raise HTTPException(400, "不支持此附件格式，请使用常用图片、文档、图稿或视频格式")
    signatures = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".pdf": b"%PDF-"}
    if extension in signatures and not content.startswith(signatures[extension]):
        raise HTTPException(400, "文件内容与扩展名不匹配")
    if extension == ".webp" and not (content.startswith(b"RIFF") and content[8:12] == b"WEBP"):
        raise HTTPException(400, "文件内容与扩展名不匹配")


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
            first_chunk = True
            while chunk := await file.read(1024 * 1024):
                if first_chunk:
                    validate_attachment_content(file.filename, chunk)
                    first_chunk = False
                total += len(chunk)
                if total > MAX_ATTACHMENT_SIZE:
                    raise HTTPException(status_code=413, detail="附件大小不能超过20MB")
                output.write(chunk)
    except Exception:
        if os.path.exists(destination):
            os.remove(destination)
        raise
