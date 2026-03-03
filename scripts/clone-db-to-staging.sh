#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# Clone production DB → staging DB
# ═══════════════════════════════════════════════════════════════
# Usage:
#   bash scripts/clone-db-to-staging.sh
#
# Prerequisites:
#   - Production DB container (webui-db) must be running
#   - Run from the project root directory
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load .env
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

DB_USER="${DB_USER:-webui_user}"
DB_NAME="${DB_NAME:-webui}"
DUMP_FILE="./backups/staging_clone.dump"

echo "============================================"
echo " Clone Production DB → Staging DB"
echo "============================================"

# ----- Step 1: Verify production DB -----
echo ""
echo "[Step 1] Checking production DB..."

if ! docker inspect webui-db &>/dev/null; then
    echo "  ERROR: webui-db container not found."
    exit 1
fi
echo "  Production DB: webui-db (running)"

# ----- Step 2: Dump production DB -----
echo ""
echo "[Step 2] Dumping production DB..."
mkdir -p backups

docker exec webui-db pg_dump \
    -U "$DB_USER" -d "$DB_NAME" \
    --clean --if-exists -F c \
    -f /tmp/staging_clone.dump

docker cp webui-db:/tmp/staging_clone.dump "$DUMP_FILE"
docker exec webui-db rm /tmp/staging_clone.dump

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "  Dump created: $DUMP_FILE ($DUMP_SIZE)"

# ----- Step 3: Start staging DB -----
echo ""
echo "[Step 3] Starting staging DB container..."

docker compose --profile staging up -d webui-db-staging
echo "  Waiting for staging DB to be ready..."

for i in $(seq 1 12); do
    if docker exec webui-db-staging pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
        echo "  Staging DB is ready."
        break
    fi
    if [[ $i -eq 12 ]]; then
        echo "  ERROR: Staging DB failed to start."
        exit 1
    fi
    sleep 5
done

# ----- Step 4: Restore into staging DB -----
echo ""
echo "[Step 4] Restoring dump into staging DB..."

docker cp "$DUMP_FILE" webui-db-staging:/tmp/staging_clone.dump

docker exec webui-db-staging pg_restore \
    -U "$DB_USER" -d "$DB_NAME" \
    --clean --if-exists --no-owner --no-privileges \
    /tmp/staging_clone.dump || true
# pg_restore returns non-zero on warnings (e.g., "role does not exist"), which is safe to ignore

docker exec webui-db-staging rm /tmp/staging_clone.dump

echo "  Restore complete."

# ----- Step 5: Start staging Open WebUI -----
echo ""
echo "[Step 5] Starting staging Open WebUI..."

docker compose --profile staging up -d open-webui-staging

echo "  Waiting for staging Open WebUI to start..."
sleep 10

for i in $(seq 1 6); do
    if curl -sf http://127.0.0.1:${STAGING_WEBUI_PORT:-10088}/health > /dev/null 2>&1; then
        echo "  Health check passed."
        break
    fi
    if [[ $i -eq 6 ]]; then
        echo "  Not ready yet. Check: docker logs open-webui-staging"
    else
        echo "  Attempt ${i}/6 - waiting 10s..."
        sleep 10
    fi
done

# ----- Step 6 (optional): Import Skills & Tools -----
echo ""
echo "[Step 6] Import Skills & Tools"

STAGING_URL="http://127.0.0.1:${STAGING_WEBUI_PORT:-10088}"

if [[ -n "${OPENWEBUI_API_KEY:-}" ]]; then
    echo "  API key found. Importing skills and tools..."
    bash "$SCRIPT_DIR/import-skills-tools.sh" "$STAGING_URL" "$OPENWEBUI_API_KEY" || true
else
    echo "  [SKIP] No OPENWEBUI_API_KEY set."
    echo "  To auto-import, run:"
    echo "    OPENWEBUI_API_KEY=<your-key> bash scripts/import-skills-tools.sh $STAGING_URL"
fi

# ----- Done -----
echo ""
echo "============================================"
echo " Staging environment ready!"
echo "============================================"
echo ""
echo " Staging Open WebUI: $STAGING_URL"
echo " Staging DB:         127.0.0.1:${STAGING_DB_PORT:-5433}"
echo ""
echo " To import skills/tools (if not done above):"
echo "   bash scripts/import-skills-tools.sh $STAGING_URL <api_key>"
echo ""
echo " To test SSO, set these env vars in .env and restart:"
echo "   STAGING_WEBUI_URL=https://your-staging-url"
echo "   (plus any OAUTH_* overrides)"
echo ""
echo " To stop staging:"
echo "   docker compose --profile staging down"
echo ""
echo " To reset staging DB (start fresh from production):"
echo "   docker compose --profile staging down -v"
echo "   bash scripts/clone-db-to-staging.sh"
echo ""
