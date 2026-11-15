#!/usr/bin/env bash
# Creates .env from .env.example with freshly generated random secrets (idempotent: refuses to overwrite).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env already exists - delete it first to regenerate."; exit 1; }
rand() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "${1:-24}"; }
cp .env.example .env
for k in MYSQL_ROOT_PASSWORD AUTH_DB_PASSWORD USER_DB_PASSWORD CONTENT_DB_PASSWORD VIDEO_DB_PASSWORD WATCHLIST_DB_PASSWORD HISTORY_DB_PASSWORD MINIO_ROOT_PASSWORD; do
  sed -i.bak "s|^$k=.*|$k=$(rand 24)|" .env
done
sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$(rand 64)|" .env && rm -f .env.bak
echo "Created .env with random secrets. Sample logins: see README (admin@hotstar-demo.com / Admin@12345)."
