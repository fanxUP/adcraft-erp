"""Application branding persistence and logo validation."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_security import safe_upload_name
from app.models.system_branding import SYSTEM_BRANDING_ID, SystemBranding

MAX_LOGO_SIZE = 2 * 1024 * 1024
DEFAULT_APP_NAME = "AdCraft ERP"

_LOGO_RULES = {
    ".jpg": {"mime_types": {"image/jpeg", "image/jpg"}, "signature": b"\xff\xd8\xff"},
    ".jpeg": {"mime_types": {"image/jpeg", "image/jpg"}, "signature": b"\xff\xd8\xff"},
    ".png": {"mime_types": {"image/png"}, "signature": b"\x89PNG\r\n\x1a\n"},
    ".webp": {"mime_types": {"image/webp"}, "signature": b"RIFF"},
}

_CANONICAL_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def validate_logo(filename: str | None, content_type: str | None, contents: bytes) -> str:
    """Validate a logo using extension, declared type, size and magic bytes."""

    suffix = Path(filename or "").suffix.lower()
    rule = _LOGO_RULES.get(suffix)
    if rule is None:
        raise ValueError("logo 仅支持 JPG、PNG、WEBP 格式")
    if len(contents) == 0:
        raise ValueError("logo 文件不能为空")
    if len(contents) > MAX_LOGO_SIZE:
        raise ValueError("logo 文件不能超过2MB")

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in rule["mime_types"]:
        raise ValueError("logo 文件格式或内容不匹配")

    signature = rule["signature"]
    if suffix == ".webp":
        valid_signature = len(contents) >= 12 and contents.startswith(signature) and contents[8:12] == b"WEBP"
    else:
        valid_signature = contents.startswith(signature)
    if not valid_signature:
        raise ValueError("logo 文件格式或内容不匹配")
    return suffix


async def get_branding(db: AsyncSession) -> SystemBranding | None:
    result = await db.execute(
        select(SystemBranding).where(SystemBranding.id == SYSTEM_BRANDING_ID)
    )
    return result.scalar_one_or_none()


async def get_or_create_branding(db: AsyncSession) -> SystemBranding:
    branding = await get_branding(db)
    if branding is None:
        branding = SystemBranding(id=SYSTEM_BRANDING_ID, logo_version=1)
        db.add(branding)
        await db.flush()
    return branding


def public_branding_payload(app_name: str | None, branding: SystemBranding | None) -> dict:
    """Return only the metadata safe to expose before authentication."""

    name = (app_name or "").strip() or DEFAULT_APP_NAME
    has_custom_logo = bool(branding and branding.logo_data)
    version = int(getattr(branding, "logo_version", 0) or 0) if has_custom_logo else 0
    return {
        "app_name": name,
        "logo_url": f"/api/v1/public/branding/logo?v={version}" if has_custom_logo else None,
        "logo_version": version,
        "has_custom_logo": has_custom_logo,
    }


def admin_branding_payload(app_name: str | None, branding: SystemBranding | None) -> dict:
    payload = public_branding_payload(app_name, branding)
    payload.update(
        {
            "logo_filename": getattr(branding, "logo_filename", None) if branding else None,
            "logo_content_type": getattr(branding, "logo_content_type", None) if branding else None,
            "logo_size": getattr(branding, "logo_size", None) if branding else None,
        }
    )
    return payload


async def replace_logo(
    db: AsyncSession,
    file: UploadFile,
    updated_by: UUID,
    app_name: str | None = None,
) -> dict:
    contents = await file.read(MAX_LOGO_SIZE + 1)
    safe_extension = validate_logo(file.filename, file.content_type, contents)
    branding = await get_or_create_branding(db)
    _, display_name = safe_upload_name(file.filename, "logo")

    branding.logo_data = contents
    branding.logo_content_type = _CANONICAL_CONTENT_TYPES[safe_extension]
    branding.logo_filename = (display_name or f"logo{safe_extension}")[:255]
    branding.logo_size = len(contents)
    branding.logo_version = max(int(branding.logo_version or 0), 0) + 1
    branding.updated_by = updated_by
    await db.flush()
    return admin_branding_payload(app_name, branding)


async def remove_logo(db: AsyncSession, updated_by: UUID, app_name: str | None = None) -> dict:
    branding = await get_or_create_branding(db)
    branding.logo_data = None
    branding.logo_content_type = None
    branding.logo_filename = None
    branding.logo_size = None
    branding.logo_version = max(int(branding.logo_version or 0), 0) + 1
    branding.updated_by = updated_by
    await db.flush()
    return admin_branding_payload(app_name, branding)
