#!/usr/bin/env python3
"""Create/verify/restore attachment backups, separately from the SQL archive.

Restore only into an empty staging directory. Never overwrite the live store.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def digest(stream):
    result = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        result.update(block)
    return result.hexdigest()


def create(root: Path, target: Path):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("附件目录不存在或为符号链接")
    if target.exists():
        raise ValueError("备份文件已存在")
    manifest = {}
    handle, temporary = tempfile.mkstemp(prefix=".uploads-", suffix=".tmp", dir=target.parent)
    os.close(handle)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for file in sorted(root.rglob("*")):
                if file.is_symlink():
                    raise ValueError("附件目录不能包含符号链接")
                if file.is_dir():
                    continue
                if not file.is_file():
                    raise ValueError("附件目录包含非常规文件")
                name = "uploads/" + file.relative_to(root).as_posix()
                # Snapshot each file to a spool: its manifest and archive must
                # describe identical bytes even during a concurrent upload.
                with file.open("rb") as source, tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as snapshot:
                    shutil.copyfileobj(source, snapshot, 1024 * 1024)
                    size = snapshot.tell()
                    snapshot.seek(0)
                    checksum = digest(snapshot)
                    snapshot.seek(0)
                    info = tarfile.TarInfo(name)
                    info.size, info.mode = size, 0o640
                    archive.addfile(info, snapshot)
                manifest[name] = {"size": size, "sha256": checksum}
            data = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size, info.mode = len(data), 0o600
            archive.addfile(info, io.BytesIO(data))
        verify(Path(temporary))
        os.chmod(temporary, 0o660)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify(path: Path):
    if path.is_symlink():
        raise ValueError("备份不能是符号链接")
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or names.count("manifest.json") != 1:
            raise ValueError("备份成员重复或缺少清单")
        for member in members:
            parts = PurePosixPath(member.name).parts
            if not member.isfile() or ".." in parts or "\\" in member.name or member.name.startswith("/"):
                raise ValueError("备份含非法路径或链接")
            if member.name != "manifest.json" and (len(parts) < 2 or parts[0] != "uploads"):
                raise ValueError("备份含意外成员")
        manifest_info = archive.getmember("manifest.json")
        if manifest_info.size > 20 * 1024 * 1024:
            raise ValueError("附件清单过大")
        manifest = json.load(archive.extractfile(manifest_info))
        if not isinstance(manifest, dict) or set(manifest) != set(names) - {"manifest.json"}:
            raise ValueError("备份清单与成员不一致")
        for name, expected in manifest.items():
            member = archive.getmember(name)
            with archive.extractfile(member) as source:
                if member.size != expected["size"] or digest(source) != expected["sha256"]:
                    raise ValueError("附件校验失败")
    return manifest


def restore(path: Path, destination: Path):
    manifest = verify(path)
    if destination.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        raise ValueError("请提供空的隔离恢复目录，禁止覆盖现有附件")
    destination.mkdir(parents=True, exist_ok=True, mode=0o750)
    with tarfile.open(path, "r:gz") as archive:
        for name in manifest:
            output = destination.joinpath(*PurePosixPath(name).parts[1:])
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            with archive.extractfile(name) as source, output.open("xb") as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
            output.chmod(0o640)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("create", "verify", "restore"))
    parser.add_argument("archive", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.operation == "create":
        if not args.root:
            parser.error("create requires --root")
        create(args.root, args.archive)
    elif args.operation == "restore":
        if not args.destination:
            parser.error("restore requires --destination (empty staging directory)")
        restore(args.archive, args.destination)
    else:
        verify(args.archive)
    print("附件备份校验完成")


if __name__ == "__main__":
    main()
