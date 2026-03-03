#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Import Skills & Tools into Open WebUI via API
# =============================================================================
# Usage:
#   bash scripts/import-skills-tools.sh [webui_url] [api_key]
#
# Environment variables (alternative to arguments):
#   OPENWEBUI_API_URL  - e.g. http://127.0.0.1:10085
#   OPENWEBUI_API_KEY  - Bearer token (Settings > Account > API Keys)
#
# What it does:
#   1. Reads all skills/*.md files, parses YAML frontmatter, and POSTs to
#      /api/v1/skills/create (skips if already exists)
#   2. Reads all tools/*.py files, parses docstring metadata, and POSTs to
#      /api/v1/tools/create (skips if already exists)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_DIR="$PROJECT_DIR/openwebui-skills"

API_URL="${1:-${OPENWEBUI_API_URL:-http://127.0.0.1:10085}}"
API_KEY="${2:-${OPENWEBUI_API_KEY:-}}"

# Remove trailing slash
API_URL="${API_URL%/}"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
if [[ -z "$API_KEY" ]]; then
    echo "ERROR: API key required."
    echo ""
    echo "Usage:"
    echo "  bash $0 [webui_url] <api_key>"
    echo ""
    echo "  Or set OPENWEBUI_API_KEY environment variable."
    echo "  Get your key from: Open WebUI > Settings > Account > API Keys"
    exit 1
fi

if [[ ! -d "$SKILLS_DIR/skills" ]]; then
    echo "ERROR: Skills directory not found: $SKILLS_DIR/skills"
    exit 1
fi

echo "============================================"
echo " Import Skills & Tools into Open WebUI"
echo "============================================"
echo ""
echo " API URL    : $API_URL"
echo " Skills dir : $SKILLS_DIR/skills/"
echo " Tools dir  : $SKILLS_DIR/tools/"
echo ""

# ---------------------------------------------------------------------------
# Helper: API call with error handling
# ---------------------------------------------------------------------------
api_post() {
    local endpoint="$1"
    local data="$2"
    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}${endpoint}" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$data" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')

    echo "$http_code|$body"
}

api_get() {
    local endpoint="$1"
    curl -s \
        -X GET "${API_URL}${endpoint}" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" 2>&1
}

# ---------------------------------------------------------------------------
# Check API connectivity
# ---------------------------------------------------------------------------
echo "[CHECK] Testing API connectivity..."
HEALTH=$(curl -sf "${API_URL}/health" 2>&1 || true)
if [[ -z "$HEALTH" ]]; then
    echo "  ERROR: Cannot reach ${API_URL}/health"
    echo "  Is Open WebUI running?"
    exit 1
fi
echo "  OK"
echo ""

# ---------------------------------------------------------------------------
# Collect existing Skills & Tools (to skip duplicates)
# ---------------------------------------------------------------------------
echo "[CHECK] Fetching existing skills and tools..."

EXISTING_SKILLS=$(api_get "/api/v1/skills/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for s in data:
            print(s.get('id', ''))
    elif isinstance(data, dict) and 'items' in data:
        for s in data['items']:
            print(s.get('id', ''))
except:
    pass
" 2>/dev/null || true)

EXISTING_TOOLS=$(api_get "/api/v1/tools/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for t in data:
            print(t.get('id', ''))
    elif isinstance(data, dict) and 'items' in data:
        for t in data['items']:
            print(t.get('id', ''))
except:
    pass
" 2>/dev/null || true)

echo "  Existing skills: $(echo "$EXISTING_SKILLS" | grep -c . || echo 0)"
echo "  Existing tools:  $(echo "$EXISTING_TOOLS" | grep -c . || echo 0)"
echo ""

# ---------------------------------------------------------------------------
# Import Skills
# ---------------------------------------------------------------------------
echo "============================================"
echo " Importing Skills"
echo "============================================"
echo ""

SKILL_OK=0
SKILL_SKIP=0
SKILL_FAIL=0

for md_file in "$SKILLS_DIR"/skills/*.md; do
    [[ -f "$md_file" ]] || continue

    filename=$(basename "$md_file" .md)

    # Parse YAML frontmatter
    skill_name=$(sed -n '/^---$/,/^---$/{ /^name:/s/^name:[[:space:]]*//p }' "$md_file")
    skill_desc=$(sed -n '/^---$/,/^---$/{ /^description:/s/^description:[[:space:]]*//p }' "$md_file")

    # Fallback to filename if frontmatter missing
    skill_id="${skill_name:-$filename}"
    skill_desc="${skill_desc:-Imported from $filename.md}"

    # Check if already exists
    if echo "$EXISTING_SKILLS" | grep -qx "$skill_id"; then
        echo "  [SKIP] $skill_id (already exists)"
        SKILL_SKIP=$((SKILL_SKIP + 1))
        continue
    fi

    # Read full file content
    content=$(cat "$md_file")

    # Build JSON payload using python for safe escaping
    json_payload=$(python3 -c "
import json, sys
content = sys.stdin.read()
payload = {
    'id': '$skill_id',
    'name': '$skill_id',
    'description': $(python3 -c "import json; print(json.dumps('$skill_desc'))"),
    'content': content,
    'meta': {'tags': []},
    'is_active': True
}
print(json.dumps(payload))
" <<< "$content")

    result=$(api_post "/api/v1/skills/create" "$json_payload")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2-)

    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        echo "  [OK]   $skill_id"
        SKILL_OK=$((SKILL_OK + 1))
    elif echo "$body" | grep -qi "already exists\|duplicate\|conflict"; then
        echo "  [SKIP] $skill_id (already exists)"
        SKILL_SKIP=$((SKILL_SKIP + 1))
    else
        echo "  [FAIL] $skill_id (HTTP $http_code)"
        echo "         $body" | head -1
        SKILL_FAIL=$((SKILL_FAIL + 1))
    fi
done

echo ""
echo "  Skills: $SKILL_OK imported, $SKILL_SKIP skipped, $SKILL_FAIL failed"
echo ""

# ---------------------------------------------------------------------------
# Import Tools
# ---------------------------------------------------------------------------
echo "============================================"
echo " Importing Tools"
echo "============================================"
echo ""

TOOL_OK=0
TOOL_SKIP=0
TOOL_FAIL=0

for py_file in "$SKILLS_DIR"/tools/*.py; do
    [[ -f "$py_file" ]] || continue

    filename=$(basename "$py_file" .py)

    # Parse docstring metadata
    tool_title=$(sed -n 's/^title:[[:space:]]*//p' "$py_file" | head -1)
    tool_desc=$(sed -n '/^description:/,/^[a-z_]*:/{ /^description:/s/^description:[[:space:]]*//p }' "$py_file" | head -1)

    # Use filename as ID (replace _ with -, strip _tool suffix for cleaner ID)
    tool_id="${filename}"
    tool_name="${tool_title:-$filename}"
    tool_desc="${tool_desc:-Imported from $filename.py}"

    # Check if already exists
    if echo "$EXISTING_TOOLS" | grep -qx "$tool_id"; then
        echo "  [SKIP] $tool_id (already exists)"
        TOOL_SKIP=$((TOOL_SKIP + 1))
        continue
    fi

    # Read full file content and build JSON
    json_payload=$(python3 -c "
import json, sys
content = sys.stdin.read()
payload = {
    'id': '$tool_id',
    'name': '$tool_name',
    'content': content,
    'meta': {
        'description': '$tool_desc',
        'manifest': {}
    },
    'access_grants': []
}
print(json.dumps(payload))
" < "$py_file")

    result=$(api_post "/api/v1/tools/create" "$json_payload")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2-)

    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        echo "  [OK]   $tool_id ($tool_name)"
        TOOL_OK=$((TOOL_OK + 1))
    elif echo "$body" | grep -qi "already exists\|duplicate\|conflict"; then
        echo "  [SKIP] $tool_id (already exists)"
        TOOL_SKIP=$((TOOL_SKIP + 1))
    else
        echo "  [FAIL] $tool_id (HTTP $http_code)"
        echo "         $body" | head -1
        TOOL_FAIL=$((TOOL_FAIL + 1))
    fi
done

echo ""
echo "  Tools: $TOOL_OK imported, $TOOL_SKIP skipped, $TOOL_FAIL failed"
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================"
echo " Import Complete"
echo "============================================"
echo ""
echo " Skills : $SKILL_OK imported, $SKILL_SKIP skipped, $SKILL_FAIL failed"
echo " Tools  : $TOOL_OK imported, $TOOL_SKIP skipped, $TOOL_FAIL failed"
echo ""

if [[ $TOOL_OK -gt 0 ]]; then
    echo " IMPORTANT: Configure Tool Valves (gear icon) for each tool:"
    echo "   - SCRIPTS_DIR: /app/OpenWebUI-Skills/vendor/<toolname>"
    echo "   - TEMP_DIR, LIBREOFFICE_PATH, etc. as needed"
    echo ""
    echo " See: openwebui-skills/INSTALLATION_GUIDE.md"
fi

echo ""
TOTAL_FAIL=$((SKILL_FAIL + TOOL_FAIL))
if [[ $TOTAL_FAIL -gt 0 ]]; then
    exit 1
fi
