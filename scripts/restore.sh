#!/usr/bin/env bash
# Restauration. Usage : DATABASE_URL_PG="postgres://..." ./scripts/restore.sh backups/fichier.sql
# ATTENTION : restaurer dans une base de TEST vide, jamais sur la base de travail.
set -euo pipefail
: "${DATABASE_URL_PG:?Définir DATABASE_URL_PG}"
psql "$DATABASE_URL_PG" < "$1"
echo "Restauration terminée."
