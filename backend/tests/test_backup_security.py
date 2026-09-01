import io
import tarfile

import app.api.backup as backup


def _write_archive(path, member_name=None, member_type=tarfile.REGTYPE):
    member_name = member_name or f"{path.name.removesuffix('.tar.gz')}.sql"
    payload = b"-- test backup\n"
    with tarfile.open(path, mode="w:gz") as archive:
        member = tarfile.TarInfo(member_name)
        member.size = len(payload)
        member.type = member_type
        archive.addfile(member, io.BytesIO(payload) if member.isfile() else None)


def test_safe_backup_path_rejects_traversal_and_symlinks(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path)
    valid = tmp_path / "backup_20260901_030709.tar.gz"
    valid.write_bytes(b"archive")

    assert backup._safe_backup_path(valid.name) == valid
    assert backup._safe_backup_path("../backup_20260901_030709.tar.gz") is None
    assert backup._safe_backup_path("backup_20260230_030709.tar.gz") is None

    link = tmp_path / "backup_20260901_030710.tar.gz"
    link.symlink_to(valid)
    assert backup._safe_backup_path(link.name) is None


def test_validate_backup_archive_accepts_only_one_expected_sql(tmp_path):
    valid = tmp_path / "backup_20260901_030709.tar.gz"
    _write_archive(valid)
    assert backup._validate_backup_archive(valid) is None

    invalid = tmp_path / "backup_20260901_030710.tar.gz"
    _write_archive(invalid, "../outside.sql")
    assert backup._validate_backup_archive(invalid) is not None
