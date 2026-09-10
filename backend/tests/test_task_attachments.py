from io import BytesIO
import stat
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app.api import tasks as task_api
from app.api.tasks import (
    INSTALLATION_PHOTO_MAX_BYTES,
    validate_installation_photo,
)


def test_validate_installation_photo_accepts_supported_signatures():
    assert validate_installation_photo(
        "image/jpeg", b"\xff\xd8\xff" + b"jpeg-data"
    ) == (None, ".jpg")
    assert validate_installation_photo(
        "image/png", b"\x89PNG\r\n\x1a\n" + b"png-data"
    ) == (None, ".png")
    assert validate_installation_photo(
        "image/webp", b"RIFF" + b"0000" + b"WEBP" + b"webp-data"
    ) == (None, ".webp")


def test_validate_installation_photo_rejects_wrong_type_or_signature():
    message, extension = validate_installation_photo("application/pdf", b"%PDF")
    assert "JPG" in message
    assert extension is None

    message, extension = validate_installation_photo("image/jpeg", b"not-an-image")
    assert "有效图片" in message
    assert extension is None


def test_validate_installation_photo_rejects_oversized_content():
    message, extension = validate_installation_photo(
        "image/jpeg", b"\xff\xd8\xff" + b"0" * INSTALLATION_PHOTO_MAX_BYTES
    )
    assert "10MB" in message
    assert extension is None


def _installation_uploader():
    return SimpleNamespace(
        id=uuid4(),
        roles=[
            SimpleNamespace(
                permissions=[SimpleNamespace(code=task_api.PERM_INSTALLATION_TASK_UPDATE)]
            )
        ],
    )


@pytest.mark.asyncio
async def test_installation_upload_forces_photo_category_and_safe_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    attachment = {"id": str(uuid4()), "category": "photo"}

    with patch.object(task_api, "AttachmentService") as service_cls:
        service_cls.return_value.add_attachment = AsyncMock(return_value=attachment)
        result = await task_api.upload_attachment(
            related_type="installation_task",
            related_id=str(uuid4()),
            category="file",
            file=UploadFile(
                filename="../../unsafe.name.exe",
                file=BytesIO(b"\xff\xd8\xff" + b"jpeg-data"),
                headers={"content-type": "image/jpeg"},
            ),
            db=db,
            current_user=_installation_uploader(),
        )

    assert result["code"] == 0
    assert result["data"] == attachment
    payload = service_cls.return_value.add_attachment.await_args.kwargs
    assert payload["data"]["category"] == "photo"
    assert payload["data"]["file_path"].endswith(".jpg")
    uploaded_files = list(tmp_path.rglob("*.jpg"))
    assert uploaded_files
    assert stat.S_IMODE(uploaded_files[0].stat().st_mode) == 0o640
    assert stat.S_IMODE(uploaded_files[0].parent.stat().st_mode) == 0o750


@pytest.mark.asyncio
async def test_installation_upload_rejects_invalid_image_before_creating_attachment(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(id=uuid4()))

    with patch.object(task_api, "AttachmentService") as service_cls:
        service_cls.return_value.add_attachment = AsyncMock()
        result = await task_api.upload_attachment(
            related_type="installation_task",
            related_id=str(uuid4()),
            file=UploadFile(
                filename="not-a-photo.jpg",
                file=BytesIO(b"plain text"),
                headers={"content-type": "image/jpeg"},
            ),
            db=db,
            current_user=_installation_uploader(),
        )

    assert result["code"] == 40001
    assert "有效图片" in result["message"]
    service_cls.return_value.add_attachment.assert_not_awaited()
    assert not list(tmp_path.rglob("*"))


@pytest.mark.asyncio
async def test_installation_upload_requires_installation_update_permission():
    db = MagicMock()
    db.get = AsyncMock()
    production_user = SimpleNamespace(
        id=uuid4(),
        roles=[
            SimpleNamespace(
                permissions=[SimpleNamespace(code=task_api.PERM_PRODUCTION_TASK_UPDATE)]
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        await task_api.upload_attachment(
            related_type="installation_task",
            related_id=str(uuid4()),
            file=UploadFile(filename="photo.jpg", file=BytesIO(b"not-used")),
            db=db,
            current_user=production_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "没有该附件关联对象的上传权限"
    db.get.assert_not_awaited()
