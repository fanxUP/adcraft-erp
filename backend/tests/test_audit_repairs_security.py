import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI, HTTPException, UploadFile
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.files import router, file_viewer
from app.core.database import get_db
from app.core.file_security import read_upload, validate_attachment_content
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_upload_url_requires_authentication_and_sandboxes_active_content(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    (tmp_path / "inert.html").write_text("<html>synthetic</html>")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/uploads/inert.html")).status_code == 401
        app.dependency_overrides[file_viewer] = lambda: SimpleNamespace()
        monkeypatch.setattr("app.api.files.can_read_upload", AsyncMock(return_value=True))
        response = await client.get("/uploads/inert.html")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment")
        assert "sandbox" in response.headers["content-security-policy"]
        assert response.headers["cache-control"] == "private, no-store"
        monkeypatch.setattr("app.api.files.can_read_upload", AsyncMock(return_value=False))
        assert (await client.get("/uploads/inert.html")).status_code == 404


@pytest.mark.asyncio
async def test_upload_size_and_content_guards():
    file = UploadFile(filename="x.png", file=io.BytesIO(b"12345"))
    with pytest.raises(HTTPException) as caught:
        await read_upload(file, max_bytes=4)
    assert caught.value.status_code == 413
    with pytest.raises(HTTPException):
        validate_attachment_content("x.png", b"<html>")
    with pytest.raises(HTTPException):
        validate_attachment_content("x.html", b"<html>")


def test_upload_backup_roundtrip_and_tampered_archive(tmp_path):
    tool = load_tool("uploads_backup")
    source = tmp_path / "source"
    source.mkdir()
    (source / "合成附件.txt").write_text("合成内容")
    archive = tmp_path / "uploads.tar.gz"
    tool.create(source, archive)
    assert len(tool.verify(archive)) == 1
    restored = tmp_path / "restored"
    tool.restore(archive, restored)
    assert (restored / "合成附件.txt").read_text() == "合成内容"
    with pytest.raises(ValueError, match="隔离恢复目录"):
        tool.restore(archive, restored)
    attack = tmp_path / "attack.tar.gz"
    with tarfile.open(attack, "w:gz") as tar:
        entry = tarfile.TarInfo("../outside")
        entry.size = 1
        tar.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        tool.restore(attack, tmp_path / "unsafe")
    assert not (tmp_path / "outside").exists()


def test_backup_sync_fails_on_tool_error_and_never_deletes_remote(tmp_path):
    import os
    binary = tmp_path / "rclone"
    binary.write_text("#!/bin/sh\necho simulated-failure\nexit 42\n")
    binary.chmod(0o700)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "RCLONE_REMOTE": "dummy:backup", "BACKUP_DIR": str(tmp_path)}
    result = subprocess.run(["bash", str(ROOT / "scripts/backup_sync.sh")], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "备份已同步" not in result.stdout
    script = (ROOT / "scripts/backup_sync.sh").read_text()
    assert "rclone sync" not in script


def test_backup_verification_failure_is_not_reported_as_success(tmp_path):
    import os
    binary = tmp_path / "rclone"
    binary.write_text('#!/bin/sh\nif [ "$1" = "copy" ]; then exit 0; fi\necho verification-failed\nexit 42\n')
    binary.chmod(0o700)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "RCLONE_REMOTE": "dummy:backup", "BACKUP_DIR": str(tmp_path)}
    result = subprocess.run(["bash", str(ROOT / "scripts/backup_sync.sh")], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "备份已同步" not in result.stdout


def test_nginx_upload_alias_replaced_without_public_cache():
    text = load_tool("private_uploads_nginx").rewrite("server { location /uploads/ { alias /secret/; expires 30d; } }")
    assert "alias" not in text and "expires" not in text
    assert "proxy_pass http://127.0.0.1:8000" in text
