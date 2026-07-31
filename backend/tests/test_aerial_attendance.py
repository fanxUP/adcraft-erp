"""Tests for AerialService attendance methods (aerial_attendance_records)."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.aerial_service import AerialService
from tests.conftest import SAMPLE_USER_ID

SAMPLE_ATTENDANCE_ID = "11112222-3333-4444-5555-666677778888"
SAMPLE_VEHICLE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SAMPLE_PERSONNEL_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def make_mock_attendance(**kwargs):
    a = MagicMock()
    a.id = kwargs.get("id", SAMPLE_ATTENDANCE_ID)
    a.att_date = kwargs.get("att_date", date(2026, 7, 31))
    a.target_type = kwargs.get("target_type", "vehicle")
    a.vehicle_id = kwargs.get("vehicle_id", SAMPLE_VEHICLE_ID)
    a.personnel_id = kwargs.get("personnel_id", None)
    a.status = kwargs.get("status", "present")
    a.check_in_time = kwargs.get("check_in_time", datetime(2026, 7, 31, 8, 0))
    a.check_out_time = kwargs.get("check_out_time", datetime(2026, 7, 31, 17, 30))
    a.overtime_hours = kwargs.get("overtime_hours", 0)
    a.remark = kwargs.get("remark", None)
    a.source = kwargs.get("source", "manual_input")
    a.created_at = kwargs.get("created_at", datetime(2026, 7, 31, 9, 0))
    a.updated_at = kwargs.get("updated_at", datetime(2026, 7, 31, 9, 0))
    return a


def make_mock_user():
    u = MagicMock()
    u.id = SAMPLE_USER_ID
    return u


@pytest.fixture
def service():
    repo = MagicMock()
    repo.list_attendance = AsyncMock(return_value=([], 0))
    repo.get_attendance = AsyncMock()
    repo.get_attendance_by_key = AsyncMock(return_value=None)
    repo.create_attendance = AsyncMock()
    repo.update_attendance = AsyncMock()
    repo.delete_attendance = AsyncMock()
    repo.create_audit_log = AsyncMock()
    with patch("app.services.aerial_service.AerialRepository") as MockRepoClass:
        MockRepoClass.return_value = repo
        svc = AerialService(AsyncMock(), make_mock_user(), "127.0.0.1")
        svc.repo = repo
        yield svc


# ── list ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_attendance(service):
    a = make_mock_attendance()
    service.repo.list_attendance.return_value = ([a], 1)
    items, total = await service.list_attendance(target_type="vehicle")
    assert total == 1
    assert items[0]["att_date"] == "2026-07-31"
    assert items[0]["target_type"] == "vehicle"
    assert items[0]["status"] == "present"
    assert items[0]["vehicle_id"] == SAMPLE_VEHICLE_ID
    assert items[0]["overtime_hours"] == 0


@pytest.mark.asyncio
async def test_list_attendance_empty(service):
    items, total = await service.list_attendance(target_type="personnel")
    assert items == []
    assert total == 0


# ── create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_attendance(service):
    a = make_mock_attendance()
    service.repo.create_attendance.return_value = a
    result = await service.create_attendance({
        "att_date": "2026-07-31",
        "target_type": "vehicle",
        "vehicle_id": SAMPLE_VEHICLE_ID,
        "status": "present",
    })
    assert result["id"] == SAMPLE_ATTENDANCE_ID
    assert result["status"] == "present"
    service.repo.create_attendance.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_attendance_personnel(service):
    a = make_mock_attendance(target_type="personnel", personnel_id=SAMPLE_PERSONNEL_ID, vehicle_id=None)
    service.repo.create_attendance.return_value = a
    result = await service.create_attendance({
        "att_date": "2026-07-31",
        "target_type": "personnel",
        "personnel_id": SAMPLE_PERSONNEL_ID,
        "status": "half_day",
    })
    assert result["target_type"] == "personnel"
    assert result["personnel_id"] == SAMPLE_PERSONNEL_ID


@pytest.mark.asyncio
async def test_create_attendance_duplicate_raises(service):
    service.repo.get_attendance_by_key.return_value = make_mock_attendance()
    with pytest.raises(ValueError, match="已有考勤记录"):
        await service.create_attendance({
            "att_date": "2026-07-31",
            "target_type": "vehicle",
            "vehicle_id": SAMPLE_VEHICLE_ID,
            "status": "present",
        })
    service.repo.create_attendance.assert_not_awaited()


# ── update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_attendance_found(service):
    a = make_mock_attendance()
    service.repo.get_attendance.return_value = a
    service.repo.update_attendance.return_value = a
    result = await service.update_attendance(SAMPLE_ATTENDANCE_ID, {"status": "absent"})
    assert result["id"] == SAMPLE_ATTENDANCE_ID
    service.repo.update_attendance.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_attendance_not_found(service):
    service.repo.get_attendance.return_value = None
    with pytest.raises(ValueError, match="考勤记录不存在"):
        await service.update_attendance(SAMPLE_ATTENDANCE_ID, {"status": "absent"})


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_attendance_found(service):
    a = make_mock_attendance()
    service.repo.get_attendance.return_value = a
    service.repo.delete_attendance.return_value = a
    result = await service.delete_attendance(SAMPLE_ATTENDANCE_ID)
    assert result["id"] == SAMPLE_ATTENDANCE_ID
    service.repo.delete_attendance.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_attendance_not_found(service):
    service.repo.get_attendance.return_value = None
    with pytest.raises(ValueError, match="考勤记录不存在"):
        await service.delete_attendance(SAMPLE_ATTENDANCE_ID)


# ── 校验 ─────────────────────────────────────────────────────────────────────

def test_clean_invalid_target_type(service):
    with pytest.raises(ValueError, match="target_type"):
        service._clean_attendance_data({"att_date": "2026-07-31", "target_type": "robot", "vehicle_id": SAMPLE_VEHICLE_ID})


def test_clean_invalid_status(service):
    with pytest.raises(ValueError, match="无效的出勤状态"):
        service._clean_attendance_data({
            "att_date": "2026-07-31", "target_type": "personnel",
            "personnel_id": SAMPLE_PERSONNEL_ID, "status": "sick",
        })


def test_clean_att_date_datetime_string(service):
    clean = service._clean_attendance_data({
        "att_date": "2026-07-31T08:00:00", "target_type": "vehicle",
        "vehicle_id": SAMPLE_VEHICLE_ID, "status": "present",
    })
    assert clean["att_date"] == date(2026, 7, 31)
    assert clean["vehicle_id"] is not None
