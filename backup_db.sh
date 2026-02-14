#!/bin/bash
# Open WebUI PostgreSQL backup script

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="openwebui-postgres"
DB_USER="openwebui_admin"
DB_NAME="openwebui"

mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL database..."
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f /tmp/backup.dump

if [ $? -eq 0 ]; then
    docker cp "$CONTAINER_NAME":/tmp/backup.dump "$BACKUP_DIR/openwebui_backup_${TIMESTAMP}.dump"
    docker exec "$CONTAINER_NAME" rm /tmp/backup.dump
    echo "Backup saved: $BACKUP_DIR/openwebui_backup_${TIMESTAMP}.dump"

    # Auto-delete backups older than 7 days
    find "$BACKUP_DIR" -name "openwebui_backup_*.dump" -mtime +7 -delete
    echo "Old backups (>7 days) cleaned up."
else
    echo "ERROR: Backup failed!"
    exit 1
fi
