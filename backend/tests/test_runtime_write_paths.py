"""Regression tests for runtime file paths used by the deployed service."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.admin import _resolve_settings_env_path, _rewrite_env_file
from app.core import performance
from app.schemas.admin import SettingsUpdate


def test_settings_path_honours_explicit_runtime_env_file(monkeypatch, tmp_path):
    env_path = tmp_path / "runtime.env"
    monkeypatch.setenv("ADCRAFT_ENV_FILE", str(env_path))

    assert _resolve_settings_env_path() == str(env_path)


def test_rewrite_env_file_preserves_comments_and_updates_only_requested_keys(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# keep this comment\n"
        "APP_NAME=Old Name\n"
        "OTHER=value\n",
        encoding="utf-8",
    )

    _rewrite_env_file(
        str(env_path),
        {
            "APP_NAME": 'APP_NAME="New Name"\n',
            "OTHER": "OTHER=value\n",
            "ADDED": "ADDED=value\n",
        },
    )

    assert env_path.read_text(encoding="utf-8") == (
        "# keep this comment\n"
        "APP_NAME=\"New Name\"\n"
        "OTHER=value\n"
        "ADDED=value\n"
    )


def test_performance_logging_disables_unavailable_path(monkeypatch, tmp_path):
    blocked_path = tmp_path / "not-a-directory"
    blocked_path.write_text("file", encoding="utf-8")
    monkeypatch.setattr(performance, "PERF_LOG_DIR", str(blocked_path))

    assert performance._log_path() is None


def test_settings_update_rejects_env_injection_and_invalid_expiry():
    with pytest.raises(ValidationError):
        SettingsUpdate(APP_NAME="名称\nMALICIOUS=true")

    with pytest.raises(ValidationError):
        SettingsUpdate(JWT_EXPIRE_MINUTES=30)
