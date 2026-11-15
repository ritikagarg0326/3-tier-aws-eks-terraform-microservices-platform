#!/usr/bin/env bash
# Runs every backend test suite in a throw-away virtualenv (no Docker needed).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv && . .venv/bin/activate
pip install -q -r services/auth/requirements-dev.txt -r services/video/requirements-dev.txt -r services/content/requirements-dev.txt
pip install -q ./libs/common
echo "=== libs/common ==="; (cd libs/common && python -m pytest tests -q)
for s in gateway auth user content video watchlist history; do
  echo "=== $s ==="; (cd services/$s && python -m pytest)
done
