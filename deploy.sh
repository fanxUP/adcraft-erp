#!/bin/bash
set -e
echo "=== AdCraft ERP Deploy ==="
cd /opt/adcraft
git pull origin master
cd backend && .venv/bin/pip install -q -e . 2>/dev/null || true
PYTHONPATH=. .venv/bin/alembic upgrade head
cd /opt/adcraft/frontend && npm install --silent 2>/dev/null && npx vite build --logLevel silent && chmod -R o+rX dist/
cd /opt/adcraft/backend && PYTHONPATH=. .venv/bin/python scripts/seed_permissions.py
systemctl restart adcraft-backend && sleep 3
echo "Done"
