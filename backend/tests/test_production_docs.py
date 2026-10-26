"""Both supported production environment names disable API documentation."""

import runpy
from pathlib import Path

import pytest

from app.core.config import settings


@pytest.mark.parametrize("environment", ["production", "prod"])
def test_production_aliases_disable_all_api_documentation(environment, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", environment)
    namespace = runpy.run_path(str(Path(__file__).parents[1] / "app/main.py"))
    application = namespace["app"]

    assert application.docs_url is None
    assert application.redoc_url is None
    assert application.openapi_url is None
