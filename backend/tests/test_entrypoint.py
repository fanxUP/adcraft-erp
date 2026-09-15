"""Startup safety tests for the native/standalone entrypoint."""

from __future__ import annotations

import sys
import types

import pytest

import entrypoint


def test_run_alembic_fails_closed_when_migration_directory_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(entrypoint, "INTERNAL_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="数据库迁移目录不存在"):
        entrypoint._run_alembic()


def test_run_alembic_fails_closed_when_upgrade_fails(monkeypatch, tmp_path):
    (tmp_path / "alembic").mkdir()
    monkeypatch.setattr(entrypoint, "INTERNAL_DIR", tmp_path)

    class FakeConfig:
        def set_main_option(self, _key, _value):
            return None

    def fail_upgrade(_config, _target):
        raise RuntimeError("schema is unavailable")

    fake_alembic = types.ModuleType("alembic")
    fake_alembic.command = types.SimpleNamespace(upgrade=fail_upgrade)
    fake_alembic_config = types.ModuleType("alembic.config")
    fake_alembic_config.Config = FakeConfig
    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(sys.modules, "alembic.config", fake_alembic_config)

    with pytest.raises(RuntimeError, match="数据库迁移失败，服务未启动"):
        entrypoint._run_alembic()
