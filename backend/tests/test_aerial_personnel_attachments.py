"""Tests for AerialService personnel attachments (aerial_personnel_attachments)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.aerial_service import AerialService
from tests.conftest import SAMPLE_USER_ID

SAMPLE_PERSONNEL_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SAMPLE_ATTACHMENT_ID = "33334444-5555-6666-7777-88889999aaaa"


def make_mock_attachment(**kwargs):
    a = MagicMock()
    a.id = kwargs.get("id", SAMPLE_ATTACHMENT_ID)
    a.personnel_id = kwargs.get("personnel_id", SAMPLE_PERSONNEL_ID)
    a.attachment_type = kwargs.get("attachment_type", "license")
    a.file_url = kwargs.get("file_url", "/uploads/202607/abc.png")
    a.file_name = kwargs.get("file_name", "驾驶证.png")
    a.uploaded_by = kwargs.get("uploaded_by", None)
    a.uploaded_at = kwargs.get("uploaded_at", datetime(2026, 7, 31, 10, 0))
    a.remark = kwargs.get("remark", None)
    return a


def make_mock_personnel(**kwargs):
    p = MagicMock()
    p.id = kwargs.get("id", SAMPLE_PERSONNEL_ID)
    p.name = kwargs.get("name", "张师傅")
    p.phone = kwargs.get("phone", None)
    p.license_no = kwargs.get("license_no", None)
    p.license_type = kwargs.get("license_type", None)
    p.license_expire_date = kwargs.get("license_expire_date", None)
    p.is_external = kwargs.get("is_external", False)
    p.personnel_type = kwargs.get("personnel_type", "driver")
    p.status = kwargs.get("status", "active")
    p.remark = kwargs.get("remark", None)
    p.id_card_no = kwargs.get("id_card_no", "110101199001011234")
    p.id_card_front_url = kwargs.get("id_card_front_url", None)
    p.id_card_back_url = kwargs.get("id_card_back_url", None)
    p.bank_card_no = kwargs.get("bank_card_no", "6222021234567890")
    p.bank_name = kwargs.get("bank_name", "工商银行")
    p.bank_account_name = kwargs.get("bank_account_name", "张师傅")
    p.created_at = datetime(2026, 7, 31, 9, 0)
    p.updated_at = datetime(2026, 7, 31, 9, 0)
    return p


@pytest.fixture
def service():
    repo = MagicMock()
    repo.list_personnel_attachments = AsyncMock(return_value=[])
    repo.create_personnel_attachment = AsyncMock()
    repo.delete_personnel_attachment = AsyncMock()
    repo.get_personnel = AsyncMock()
    repo.create_audit_log = AsyncMock()
    with patch("app.services.aerial_service.AerialRepository") as MockRepoClass:
        MockRepoClass.return_value = repo
        svc = AerialService(AsyncMock(), MagicMock(id=SAMPLE_USER_ID), "127.0.0.1")
        svc.repo = repo
        yield svc


# ── list ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_personnel_attachments(service):
    a = make_mock_attachment()
    service.repo.list_personnel_attachments.return_value = [a]
    items = await service.list_personnel_attachments(SAMPLE_PERSONNEL_ID)
    assert len(items) == 1
    assert items[0]["attachment_type"] == "license"
    assert items[0]["file_url"] == "/uploads/202607/abc.png"


@pytest.mark.asyncio
async def test_list_personnel_attachments_empty(service):
    items = await service.list_personnel_attachments(SAMPLE_PERSONNEL_ID)
    assert items == []


# ── create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_personnel_attachment(service):
    service.repo.get_personnel.return_value = make_mock_personnel()
    service.repo.create_personnel_attachment.return_value = make_mock_attachment()
    file = MagicMock()
    file.filename = "x.png"
    file.read = AsyncMock(return_value=b"abc")
    result = await service.create_personnel_attachment(SAMPLE_PERSONNEL_ID, file, "license")
    assert result["id"] == SAMPLE_ATTACHMENT_ID
    assert result["personnel_id"] == SAMPLE_PERSONNEL_ID
    service.repo.create_personnel_attachment.assert_awaited_once()
    args, _ = service.repo.create_personnel_attachment.call_args
    assert args[0]["uploaded_by"] == SAMPLE_USER_ID
    assert args[0]["attachment_type"] == "license"


@pytest.mark.asyncio
async def test_create_personnel_attachment_personnel_not_found(service):
    service.repo.get_personnel.return_value = None
    file = MagicMock()
    file.filename = "x.png"
    file.read = AsyncMock(return_value=b"abc")
    with pytest.raises(ValueError, match="人员不存在"):
        await service.create_personnel_attachment(SAMPLE_PERSONNEL_ID, file, "license")
    service.repo.create_personnel_attachment.assert_not_awaited()


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_personnel_attachment_found(service):
    service.repo.delete_personnel_attachment.return_value = make_mock_attachment()
    result = await service.delete_personnel_attachment(SAMPLE_ATTACHMENT_ID)
    assert result == {"id": SAMPLE_ATTACHMENT_ID, "deleted": True}


@pytest.mark.asyncio
async def test_delete_personnel_attachment_not_found(service):
    service.repo.delete_personnel_attachment.return_value = None
    with pytest.raises(ValueError, match="附件不存在"):
        await service.delete_personnel_attachment(SAMPLE_ATTACHMENT_ID)


# ── 序列化 ───────────────────────────────────────────────────────────────────

def test_personnel_to_dict_has_identity_fields(service):
    p = make_mock_personnel()
    d = service._personnel_to_dict(p)
    assert d["id_card_no"] == "110101199001011234"
    assert d["id_card_front_url"] is None
    assert d["bank_card_no"] == "6222021234567890"
    assert d["bank_name"] == "工商银行"
    assert d["bank_account_name"] == "张师傅"


def test_save_upload_file_returns_upload_url(service):
    file = MagicMock()
    file.filename = "驾照.jpg"
    file.read = AsyncMock(return_value=b"jpegdata")

    async def run():
        return await service.save_upload_file(file)

    result = __import__("asyncio").run(run())
    assert result["file_url"].startswith("/uploads/")
    assert result["file_url"].endswith(".jpg")
    assert result["file_name"] == "驾照.jpg"
    assert result["file_size"] == 8
