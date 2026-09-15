from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import UploadFile
from starlette.requests import Request

from app.api.admin import force_relogin
from app.api.public import get_public_branding, get_public_logo
from app.core.config import settings
from app.services.branding_service import (
    MAX_LOGO_SIZE,
    public_branding_payload,
    replace_logo,
    validate_logo,
)


@pytest.mark.asyncio
async def test_force_relogin_increments_active_user_token_versions():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    response = await force_relogin(db=db, current_user=MagicMock())

    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "UPDATE users" in sql
    assert "token_version=(users.token_version + 1)" in sql
    assert "users.deleted_at IS NULL" in sql
    assert "users.is_active IS true" in sql
    db.commit.assert_awaited_once()
    assert response["code"] == 0
    assert response["data"]["message"] == "已强制所有用户重新登录"


def test_logo_validation_requires_matching_image_signature_and_type():
    assert validate_logo("brand.png", "image/png", b"\x89PNG\r\n\x1a\nrest") == ".png"

    with pytest.raises(ValueError, match="格式或内容不匹配"):
        validate_logo("brand.png", "image/png", b"not-a-png")

    with pytest.raises(ValueError, match="仅支持 JPG、PNG、WEBP"):
        validate_logo("brand.svg", "image/svg+xml", b"<svg></svg>")


def test_logo_validation_rejects_oversized_upload():
    with pytest.raises(ValueError, match="不能超过2MB"):
        validate_logo("brand.jpg", "image/jpeg", b"\xff\xd8\xff" + b"x" * MAX_LOGO_SIZE)


def test_public_branding_payload_exposes_only_safe_metadata():
    fallback = public_branding_payload("新系统", None)
    assert fallback == {
        "app_name": "新系统",
        "logo_url": None,
        "logo_version": 0,
        "has_custom_logo": False,
    }

    branding = SimpleNamespace(
        logo_data=b"image",
        logo_version=7,
        logo_content_type="image/png",
        logo_filename="logo.png",
        logo_size=5,
    )
    payload = public_branding_payload("新系统", branding)
    assert payload["logo_url"] == "/api/v1/public/branding/logo?v=7"
    assert payload["has_custom_logo"] is True
    assert "logo_data" not in payload


@pytest.mark.asyncio
async def test_replace_logo_updates_single_branding_row_without_storing_a_path():
    row = SimpleNamespace(
        id=1,
        logo_data=None,
        logo_content_type=None,
        logo_filename=None,
        logo_size=None,
        logo_version=3,
        updated_by=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: row))
    db.flush = AsyncMock()
    upload = UploadFile(
        filename="公司标志.PNG",
        file=BytesIO(b"\x89PNG\r\n\x1a\nvalid"),
        headers={"content-type": "image/png"},
    )

    result = await replace_logo(
        db,
        upload,
        UUID("11111111-1111-1111-1111-111111111111"),
    )

    assert row.logo_data == b"\x89PNG\r\n\x1a\nvalid"
    assert row.logo_content_type == "image/png"
    assert row.logo_filename == "公司标志.PNG"
    assert row.logo_size == len(row.logo_data)
    assert row.logo_version == 4
    assert result["has_custom_logo"] is True
    assert result["logo_url"].endswith("?v=4")
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_public_branding_and_logo_endpoints_expose_runtime_brand_only():
    branding = SimpleNamespace(
        logo_data=b"\x89PNG\r\n\x1a\nvalid",
        logo_version=9,
        logo_content_type="image/png",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: branding))
    original_name = settings.APP_NAME
    settings.APP_NAME = "现场管理系统"
    try:
        metadata_response = await get_public_branding(db=db)
        logo_response = await get_public_logo(
            Request({"type": "http", "method": "GET", "path": "/api/v1/public/branding/logo", "headers": []}),
            db=db,
        )
    finally:
        settings.APP_NAME = original_name

    assert metadata_response["data"]["app_name"] == "现场管理系统"
    assert metadata_response["data"]["logo_url"].endswith("?v=9")
    assert logo_response.media_type == "image/png"
    assert logo_response.body == branding.logo_data
    assert logo_response.headers["cache-control"] == "public, max-age=300"
