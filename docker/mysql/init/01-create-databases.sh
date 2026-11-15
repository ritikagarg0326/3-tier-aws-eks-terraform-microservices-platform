#!/bin/bash
# Runs once, on first start of an empty data volume.
# One schema + one dedicated MySQL account per microservice: a service can only touch its own database.
set -euo pipefail

create_db() {
  local db="$1" user="$2" pass="$3"
  mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${user}'@'%' IDENTIFIED BY '${pass}';
GRANT ALL PRIVILEGES ON \`${db}\`.* TO '${user}'@'%';
SQL
}

create_db auth_db      auth_svc      "${AUTH_DB_PASSWORD:?}"
create_db user_db      user_svc      "${USER_DB_PASSWORD:?}"
create_db content_db   content_svc   "${CONTENT_DB_PASSWORD:?}"
create_db video_db     video_svc     "${VIDEO_DB_PASSWORD:?}"
create_db watchlist_db watchlist_svc "${WATCHLIST_DB_PASSWORD:?}"
create_db history_db   history_svc   "${HISTORY_DB_PASSWORD:?}"
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "FLUSH PRIVILEGES;"
echo "hotstar: created 6 service databases"
