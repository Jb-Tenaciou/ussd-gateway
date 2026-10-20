#!/usr/bin/env bash
# Sauvegarde PostgreSQL.
# Usage : DATABASE_URL_PG="postgres://user:pwd@host:port/db?sslmode=require" ./scripts/backup.sh
set -euo pipefail
: "${DATABASE_URL_PG:?Définir DATABASE_URL_PG (URL postgres:// sans +psycopg2)}"
mkdir -p backups
FILE="backups/ussd_$(date +%Y%m%d_%H%M%S).sql"
pg_dump --no-owner --no-privileges "$DATABASE_URL_PG" > "$FILE"
echo "Sauvegarde écrite : $FILE"
