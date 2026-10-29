#!/usr/bin/env python3
"""Replace native Nginx's public uploads alias, keeping backups outside includes.

Called by deploy.sh. A failed nginx -t restores the original configurations.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess


def rewrite(text):
    pattern = r"location\s+(?:\^~\s+)?/uploads/\s*\{[^{}]*\}"
    replacement = """location ^~ /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }"""
    if not re.search(pattern, text):
        raise ValueError("没有找到可识别的 /uploads/ 配置，未修改 Nginx")
    return re.sub(pattern, replacement, text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enabled-dir", type=Path, default=Path("/etc/nginx/sites-enabled"))
    parser.add_argument("--backup-dir", type=Path, default=Path("/var/backups/adcraft-nginx"))
    args = parser.parse_args()
    originals = {}
    try:
        paths = {file.resolve() for file in args.enabled_dir.glob("adcraft*") if file.is_file()}
        if not paths:
            raise ValueError("未找到 AdCraft Nginx 站点，必须核对附件代理配置后发布")
        for path in sorted(paths):
            original = path.read_text()
            updated = rewrite(original)
            if updated == original:
                continue
            backup = args.backup_dir / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") / path.name
            backup.parent.mkdir(parents=True, mode=0o700)
            shutil.copy2(path, backup)
            originals[path] = original
            path.write_text(updated)
        subprocess.run(["nginx", "-t"], check=True)
    except Exception:
        for path, original in originals.items():
            path.write_text(original)
        raise


if __name__ == "__main__":
    main()
