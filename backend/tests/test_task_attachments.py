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
    INSTALLATION_VIDEO_MAX_BYTES,
    TASK_ATTACHMENT_FILE_MAX_BYTES,
    TASK_ATTACHMENT_IMAGE_MAX_BYTES,
    validate_task_attachment,
    validate_installation_media,
    validate_installation_photo,
)


def test_validate_task_attachment_accepts_images_and_supported_documents():
    assert validate_task_attachment(
        "design.webp", "image/webp", b"RIFF" + b"0000" + b"WEBP" + b"image"
    ) == (None, ".webp", "image")
    assert validate_task_attachment(
        "制作说明.pdf", "application/pdf", b"%PDF-1.7\ncontent"
    ) == (None, ".pdf", "pdf")
    assert validate_task_attachment(
        "材料清单.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        b"PK\x03\x04xlsx",
    ) == (None, ".xlsx", "document")
    assert validate_task_attachment(
        "图纸.dwg", "application/octet-stream", b"AC1032dwg"
    ) == (None, ".dwg", "cad")
    assert validate_task_attachment(
        "资料.zip", "application/zip", b"PK\x03\x04archive"
    ) == (None, ".zip", "archive")


def test_validate_task_attachment_accepts_video_and_rejects_unsafe_files():
    assert validate_task_attachment(
        "现场.mp4", "video/mp4", b"0000ftypisom" + b"video"
    ) == (None, ".mp4", "video")
    message, extension, category = validate_task_attachment(
        "脚本.html", "text/html", b"<script>alert(1)</script>"
    )
    assert "支持" in message
    assert extension is None
    assert category is None


def test_validate_task_attachment_rejects_mismatched_signatures_and_size_limits():
    message, extension, category = validate_task_attachment(
        "设计.jpg", "image/jpeg", b"not-an-image"
    )
    assert "有效图片" in message
    assert extension is None
    assert category is None

    message, extension, category = validate_task_attachment(
        "大文件.pdf", "application/pdf", b"%PDF-" + b"0" * TASK_ATTACHMENT_FILE_MAX_BYTES
    )
    assert "45MB" in message
    assert extension is None
    assert category is None

    message, extension, category = validate_task_attachment(
        "大图.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"0" * TASK_ATTACHMENT_IMAGE_MAX_BYTES
    )
    assert "10MB" in message
    assert extension is None
    assert category is None


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


def test_validate_installation_media_accepts_supported_video_signatures():
    assert validate_installation_media(
        "video/mp4", b"0000ftypisom" + b"mp4-data"
    ) == (None, ".mp4", "video")
    assert validate_installation_media(
        "video/webm", b"\x1a\x45\xdf\xa3" + b"webm-data"
    ) == (None, ".webm", "video")
    assert validate_installation_media(
        "video/quicktime", b"0000ftypqt  " + b"mov-data"
    ) == (None, ".mov", "video")


def test_validate_installation_media_rejects_invalid_video_or_oversized_content():
    message, extension, category = validate_installation_media(
        "video/mp4", b"not-a-video"
    )
    assert "有效视频" in message
    assert extension is None
    assert category is None

    message, extension, category = validate_installation_media(
        "video/mp4", b"0000ftypisom" + b"0" * INSTALLATION_VIDEO_MAX_BYTES
    )
    assert "45MB" in message
    assert extension is None
    assert category is None


def _installation_uploader():
    codes = [
        task_api.PERM_INSTALLATION_TASK_UPDATE,
        task_api.PERM_INSTALLATION_TASK_READ,
    ]
    return SimpleNamespace(
        id=uuid4(),
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in codes])],
    )


def _task_uploader(permission: str):
    codes = [permission]
    stage_reads = {
        task_api.PERM_DESIGN_TASK_UPDATE: task_api.PERM_DESIGN_TASK_READ,
        task_api.PERM_PRODUCTION_TASK_UPDATE: task_api.PERM_PRODUCTION_TASK_READ,
        task_api.PERM_INSTALLATION_TASK_UPDATE: task_api.PERM_INSTALLATION_TASK_READ,
    }
    if permission in stage_reads:
        codes.append(stage_reads[permission])
    return SimpleNamespace(
        id=uuid4(),
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in codes])],
    )


def _visible_task_db(task):
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalar_one_or_none=lambda: task,
        )
    )
    return db


@pytest.mark.asyncio
async def test_design_upload_accepts_document_and_sanitizes_display_name(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _visible_task_db(SimpleNamespace(id=uuid4()))
    attachment = {"id": str(uuid4()), "category": "document"}

    with patch.object(task_api, "AttachmentService") as service_cls:
        service_cls.return_value.add_attachment = AsyncMock(return_value=attachment)
        result = await task_api.upload_attachment(
            related_type="design_task",
            related_id=str(uuid4()),
            category="image",
            file=UploadFile(
                filename="../../设计说明.docx",
                file=BytesIO(b"PK\x03\x04docx-data"),
                headers={
                    "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                },
            ),
            db=db,
            current_user=_task_uploader(task_api.PERM_DESIGN_TASK_UPDATE),
        )

    assert result["code"] == 0
    payload = service_cls.return_value.add_attachment.await_args.kwargs
    assert payload["data"]["category"] == "document"
    assert payload["data"]["filename"] == "设计说明.docx"
    assert payload["data"]["file_path"].endswith(".docx")
    assert list(tmp_path.rglob("*.docx"))


@pytest.mark.asyncio
async def test_design_upload_requires_design_permission_and_existing_task():
    db = MagicMock()
    db.execute = AsyncMock()
    with pytest.raises(HTTPException) as permission_error:
        await task_api.upload_attachment(
            related_type="design_task",
            related_id=str(uuid4()),
            file=UploadFile(filename="说明.pdf", file=BytesIO(b"%PDF-1.7")),
            db=db,
            current_user=_task_uploader(task_api.PERM_PRODUCTION_TASK_UPDATE),
        )
    assert permission_error.value.status_code == 403
    db.execute.assert_not_awaited()

    db.execute.reset_mock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    result = await task_api.upload_attachment(
        related_type="design_task",
        related_id=str(uuid4()),
        file=UploadFile(filename="说明.pdf", file=BytesIO(b"%PDF-1.7")),
        db=db,
        current_user=_task_uploader(task_api.PERM_DESIGN_TASK_UPDATE),
    )
    assert result["code"] == 40401
    assert "任务不存在" in result["message"]


@pytest.mark.asyncio
async def test_delete_attachment_requires_permission_for_attachment_task_type():
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(related_type="design_task", file_path="202609/file.pdf"))
    with pytest.raises(HTTPException) as exc_info:
        await task_api.delete_attachment(
            attachment_id=str(uuid4()),
            db=db,
            current_user=_task_uploader(task_api.PERM_PRODUCTION_TASK_UPDATE),
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "没有该附件关联对象的删除权限"


@pytest.mark.asyncio
async def test_installation_upload_forces_photo_category_and_safe_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _visible_task_db(SimpleNamespace(id=uuid4()))
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
async def test_installation_video_upload_forces_video_category_and_safe_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _visible_task_db(SimpleNamespace(id=uuid4()))
    attachment = {"id": str(uuid4()), "category": "video"}

    with patch.object(task_api, "AttachmentService") as service_cls:
        service_cls.return_value.add_attachment = AsyncMock(return_value=attachment)
        result = await task_api.upload_attachment(
            related_type="installation_task",
            related_id=str(uuid4()),
            category="photo",
            file=UploadFile(
                filename="../../unsafe.name.exe",
                file=BytesIO(b"0000ftypisom" + b"mp4-data"),
                headers={"content-type": "video/mp4"},
            ),
            db=db,
            current_user=_installation_uploader(),
        )

    assert result["code"] == 0
    assert result["data"] == attachment
    payload = service_cls.return_value.add_attachment.await_args.kwargs
    assert payload["data"]["category"] == "video"
    assert payload["data"]["file_path"].endswith(".mp4")
    assert list(tmp_path.rglob("*.mp4"))


@pytest.mark.asyncio
async def test_installation_upload_rejects_invalid_image_before_creating_attachment(tmp_path, monkeypatch):
    monkeypatch.setattr(task_api.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _visible_task_db(SimpleNamespace(id=uuid4()))

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
    db.execute = AsyncMock()
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
    db.execute.assert_not_awaited()
