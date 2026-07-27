#!/bin/bash
# Unified Document Compiler daily backup: a consistent SQLite snapshot of the application
# database, plus a tar snapshot of the vector store. Run by
# udc-backup.timer once a day - not meant to be run manually except
# for testing or an ad-hoc backup before a risky admin database query.
#
# Usage: UDC_DATA_STORAGE=/opt/udc/data_storage/udc.db \
#        UDC_VECTOR_DB=/opt/udc/vector_db \
#        UDC_BACKUP_DIR=/opt/udc/backups \
#        ./backup.sh
set -euo pipefail

DATA_STORAGE="${UDC_DATA_STORAGE:-/opt/udc/data_storage/udc.db}"
VECTOR_DB="${UDC_VECTOR_DB:-/opt/udc/vector_db}"
BACKUP_DIR="${UDC_BACKUP_DIR:-/opt/udc/backups}"
RETENTION_DAYS="${UDC_BACKUP_RETENTION_DAYS:-7}"

if [ ! -f "$DATA_STORAGE" ]; then
    echo "==> No database at $DATA_STORAGE yet - nothing to back up, skipping."
    exit 0
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"

echo "==> Backing up database ($DATA_STORAGE)"
sqlite3 "$DATA_STORAGE" ".backup '$BACKUP_DIR/udc-$timestamp.db'"

echo "==> Backing up vector store ($VECTOR_DB)"
tar -czf "$BACKUP_DIR/vector_db-$timestamp.tar.gz" -C "$(dirname "$VECTOR_DB")" "$(basename "$VECTOR_DB")"

echo "==> Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -maxdepth 1 -name "udc-*.db" -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -name "vector_db-*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

echo "==> Done: $BACKUP_DIR/udc-$timestamp.db, $BACKUP_DIR/vector_db-$timestamp.tar.gz"
