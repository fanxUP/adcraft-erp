from datetime import UTC, date, datetime
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.ai.gateway.gateway import _BUSINESS_TIMEZONE, _business_today
from app.repositories.ai_request_repo import AIRequestRepository
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect


def _datetime_parameters(statement):
    compiled = statement.compile(dialect=postgresql_dialect())
    return sorted(
        value
        for value in compiled.params.values()
        if isinstance(value, datetime)
    )


@pytest.mark.asyncio
async def test_request_date_filter_uses_aware_business_day_boundaries():
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await AIRequestRepository(db).list_all(
        uuid4(),
        start_date=date(2026, 9, 30),
        end_date=date(2026, 9, 30),
    )

    count_statement = db.execute.await_args_list[0].args[0]
    assert _datetime_parameters(count_statement) == [
        datetime(2026, 9, 30, tzinfo=_BUSINESS_TIMEZONE),
        datetime(2026, 10, 1, tzinfo=_BUSINESS_TIMEZONE),
    ]


def test_ai_usage_today_uses_business_timezone():
    fake_now = datetime(2026, 9, 8, 0, 5)
    with patch("app.ai.gateway.gateway.datetime") as datetime_mock:
        datetime_mock.now.return_value = fake_now

        assert _business_today() == date(2026, 9, 8)

    datetime_mock.now.assert_called_once_with(_BUSINESS_TIMEZONE)


def test_quote_description_defaults_use_business_timezone():
    from app.ai.rule_based.quote_description_generator import (
        _BUSINESS_TIMEZONE,
        _business_today,
    )

    with patch("app.ai.rule_based.quote_description_generator.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(
            2026, 9, 9, 0, 5, tzinfo=_BUSINESS_TIMEZONE
        )

        assert _business_today() == date(2026, 9, 9)

    datetime_mock.now.assert_called_once_with(_BUSINESS_TIMEZONE)


def test_report_current_time_uses_business_timezone_as_naive_db_value():
    from app.services.report_service import (
        _BUSINESS_TIMEZONE,
        _business_now_naive,
    )

    with patch("app.services.report_service.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(
            2026, 9, 9, 0, 5, tzinfo=_BUSINESS_TIMEZONE
        )

        assert _business_now_naive() == datetime(2026, 9, 9, 0, 5)

    datetime_mock.now.assert_called_once_with(_BUSINESS_TIMEZONE)


@pytest.mark.parametrize(
    "module_name",
    [
        "app.services.payment_service",
        "app.services.vehicle_compliance_service",
        "app.services.vehicle_dispatch_service",
    ],
)
def test_legacy_utc_helpers_are_explicit_and_naive(module_name):
    module = import_module(module_name)
    expected = datetime(2026, 9, 9, 8, 0, tzinfo=UTC)

    with patch.object(module, "datetime") as datetime_mock:
        datetime_mock.now.return_value = expected
        actual = module._utc_now()

    datetime_mock.now.assert_called_once_with(UTC)
    assert actual == expected.replace(tzinfo=None)
    assert actual.tzinfo is None


def test_vehicle_registry_calendar_uses_business_timezone():
    from app.services.vehicle_registry_service import (
        _BUSINESS_TIMEZONE,
        _business_now,
    )

    with patch("app.services.vehicle_registry_service.datetime") as datetime_mock:
        expected = datetime(2026, 9, 9, 0, 5, tzinfo=_BUSINESS_TIMEZONE)
        datetime_mock.now.return_value = expected

        assert _business_now() == expected

    datetime_mock.now.assert_called_once_with(_BUSINESS_TIMEZONE)


@pytest.mark.parametrize(
    "module_name, expected, expected_month",
    [
        (
            "app.ai.api.ai_payment_ocr",
            datetime(2026, 9, 30, 23, 59, tzinfo=UTC),
            "202609",
        ),
        (
            "app.ai.api.ai_payment_ocr",
            datetime(2026, 10, 1, 0, 0, tzinfo=UTC),
            "202610",
        ),
        (
            "app.ai.api.ai_site_photo",
            datetime(2026, 9, 30, 23, 59, tzinfo=UTC),
            "202609",
        ),
        (
            "app.ai.api.ai_site_photo",
            datetime(2026, 10, 1, 0, 0, tzinfo=UTC),
            "202610",
        ),
    ],
)
def test_ai_upload_archive_month_uses_explicit_utc(
    module_name, expected, expected_month
):
    module = import_module(module_name)

    with patch.object(module, "datetime") as datetime_mock:
        datetime_mock.now.return_value = expected
        actual = module._utc_month_dir()

    datetime_mock.now.assert_called_once_with(UTC)
    assert actual == expected_month


@pytest.mark.asyncio
async def test_installation_confirmation_parses_date_only_input():
    from app.ai_assistant.tools.installation_tools import (
        create_installation_task_confirmed,
    )

    service = MagicMock()
    service.create_task = AsyncMock(return_value={"id": "task-1"})
    with patch(
        "app.services.task_service.InstallationTaskService",
        return_value=service,
    ):
        await create_installation_task_confirmed(
            db=MagicMock(),
            user=MagicMock(),
            order_id="",
            scheduled_date="2026-09-08",
        )

    payload = service.create_task.await_args.args[0]
    assert payload["scheduled_date"] == date(2026, 9, 8)
