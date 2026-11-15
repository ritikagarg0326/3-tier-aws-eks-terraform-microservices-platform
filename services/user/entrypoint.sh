#!/bin/sh
set -e
python -m hotstar_common.startup
alembic upgrade head
if [ "${SEED_DATA:-false}" = "true" ]; then
  python -m app.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002} --proxy-headers --forwarded-allow-ips='*' --workers ${WEB_CONCURRENCY:-1}
