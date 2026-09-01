#!/usr/bin/env python3
"""Validate the narrow archive format accepted by AdCraft restore."""

from __future__ import annotations

import re
import sys
import tarfile
from datetime import datetime
from pathlib import Path


BACKUP_FILENAME_RE = re.compile(r"^backup_(?P<date>\d{8})_(?P<time>\d{6})\.tar\.gz$")


def _valid_filename(path: Path) -> bool:
    match = BACKUP_FILENAME_RE.fullmatch(path.name)
    if not match:
        return False
    try:
        datetime.strptime(f"{match['date']}_{match['time']}", "%Y%m%d_%H%M%S")
    except ValueError:
        return False
    return True


def validate(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file() or not _valid_filename(path):
        return "invalid backup path or filename"

    expected_sql = f"{path.name.removesuffix('.tar.gz')}.sql"
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
    except (OSError, tarfile.TarError) as exc:
        return f"invalid tar.gz archive: {exc}"

    if len(members) != 1:
        return "archive must contain exactly one SQL file"

    member = members[0]
    if member.name != expected_sql or not member.isfile() or member.issym() or member.islnk():
        return "archive contains an unexpected member"
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_backup.py BACKUP_FILE", file=sys.stderr)
        return 2
    reason = validate(Path(sys.argv[1]))
    if reason:
        print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
