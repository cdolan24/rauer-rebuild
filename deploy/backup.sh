#!/bin/bash
# Buddharauer daily backup: a consistent SQLite snapshot of the application
# database, plus a tar snapshot of the vector store. Run by
# buddharauer-backup.timer once a day - not meant to be run manually except
# for testing or an ad-hoc backup before a risky admin database query.
#
# Usage: BUDDHARAUER_DATA_STORAGE=/opt/buddharauer/data_storage/buddharauer.db \
#        BUDDHARAUER_VECTOR_DB=/opt/buddharauer/vector_db \
#        BUDDHARAUER_BACKUP_DIR=/opt/buddharauer/backups \
#        ./backup.sh
set -euo pipefail

DATA_STORAGE="${BUDDHARAUER_DATA_STORAGE:-/opt/buddharauer/data_storage/buddharauer.db}"
VECTOR_DB="${BUDDHARAUER_VECTOR_DB:-/opt/buddharauer/vector_db}"
BACKUP_DIR="${BUDDHARAUER_BACKUP_DIR:-/opt/buddharauer/backups}"
RETENTION_DAYS="${BUDDHARAUER_BACKUP_RETENTION_DAYS:-7}"

if [ ! -f "$DATA_STORAGE" ]; then
    echo "==> No database at $DATA_STORAGE yet - nothing to back up, skipping."
    exit 0
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"

echo "==> Backing up database ($DATA_STORAGE)"
sqlite3 "$DATA_STORAGE" ".backup '$BACKUP_DIR/buddharauer-$timestamp.db'"

echo "==> Backing up vector store ($VECTOR_DB)"
tar -czf "$BACKUP_DIR/vector_db-$timestamp.tar.gz" -C "$(dirname "$VECTOR_DB")" "$(basename "$VECTOR_DB")"

echo "==> Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -maxdepth 1 -name "buddharauer-*.db" -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -name "vector_db-*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

echo "==> Done: $BACKUP_DIR/buddharauer-$timestamp.db, $BACKUP_DIR/vector_db-$timestamp.tar.gz"
