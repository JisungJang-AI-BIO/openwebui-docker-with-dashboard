#!/bin/bash
# =============================================================================
# Clone Anthropic Skills scripts into vendor/ directory
# Fetches scripts for ALL skills that need them (docx, pdf, pptx, xlsx).
# Only clones if not already present.
#
# Usage:
#   bash server-setup/clone-anthropic-scripts.sh [project_dir]
# =============================================================================

set -e

PROJ_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
VENDOR_DIR="$PROJ_DIR/vendor"

echo "============================================"
echo " Anthropic Scripts Setup (All Skills)"
echo "============================================"
echo ""
echo "Project dir : $PROJ_DIR"
echo "Vendor dir  : $VENDOR_DIR"
echo ""

# ---------------------------------------------------------------------------
# Skills that have scripts/ directories we need
# Format: skill_name -> sparse-checkout path within the anthropics/skills repo
# ---------------------------------------------------------------------------
declare -A SKILL_SCRIPTS=(
    ["docx"]="skills/docx/scripts"
    ["pdf"]="skills/pdf/scripts"
    ["pptx"]="skills/pptx/scripts"
    ["xlsx"]="skills/xlsx/scripts"
)

# Also fetch non-script resources (templates, fonts, themes)
declare -A SKILL_RESOURCES=(
    ["algorithmic-art"]="skills/algorithmic-art/templates"
    ["canvas-design"]="skills/canvas-design/canvas-fonts"
    ["theme-factory"]="skills/theme-factory/themes"
)

# Also fetch SKILL.md for all skills (for reference / Skill text conversion)
ALL_SKILLS=(
    docx pdf pptx xlsx
    mcp-builder webapp-testing web-artifacts-builder skill-creator
    slack-gif-creator frontend-design canvas-design algorithmic-art
    brand-guidelines theme-factory doc-coauthoring internal-comms
)

# ---------------------------------------------------------------------------
# Check if already cloned
# ---------------------------------------------------------------------------
MARKER="$VENDOR_DIR/.cloned"
if [ -f "$MARKER" ]; then
    echo "[SKIP] Anthropic scripts already present (marker: $MARKER)"
    echo ""
    echo "To force re-download, run:"
    echo "  rm -rf $VENDOR_DIR && bash $0 $PROJ_DIR"
    echo ""
    echo "Current vendor contents:"
    ls -1 "$VENDOR_DIR/" 2>/dev/null || echo "  (empty)"
    exit 0
fi

# ---------------------------------------------------------------------------
# Sparse clone
# ---------------------------------------------------------------------------
echo "[CLONE] Fetching Anthropic skills repository (sparse checkout) ..."

TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/anthropics/skills.git 2>&1 | tail -5

cd skills

# Build sparse-checkout paths
SPARSE_PATHS=()

# Scripts
for skill in "${!SKILL_SCRIPTS[@]}"; do
    SPARSE_PATHS+=("${SKILL_SCRIPTS[$skill]}")
done

# Resources
for skill in "${!SKILL_RESOURCES[@]}"; do
    SPARSE_PATHS+=("${SKILL_RESOURCES[$skill]}")
done

# SKILL.md files for all skills
for skill in "${ALL_SKILLS[@]}"; do
    SPARSE_PATHS+=("skills/$skill/SKILL.md")
done

# Reference / example directories (if they exist)
for skill in "${ALL_SKILLS[@]}"; do
    SPARSE_PATHS+=("skills/$skill/reference")
    SPARSE_PATHS+=("skills/$skill/examples")
done

echo ""
echo "[SPARSE] Setting checkout paths (${#SPARSE_PATHS[@]} entries) ..."
git sparse-checkout set --no-cone "${SPARSE_PATHS[@]}" 2>&1

# ---------------------------------------------------------------------------
# Copy to vendor/
# ---------------------------------------------------------------------------
echo ""
echo "[COPY] Copying to $VENDOR_DIR ..."
mkdir -p "$VENDOR_DIR"

# 1. Copy scripts for document processing skills
for skill in "${!SKILL_SCRIPTS[@]}"; do
    src_path="${SKILL_SCRIPTS[$skill]}"
    dest="$VENDOR_DIR/$skill"
    if [ -d "$src_path" ]; then
        echo "  scripts: $skill → $dest/"
        mkdir -p "$dest"
        cp -r "$src_path"/* "$dest/"
    else
        echo "  scripts: $skill — not found in repo (may not exist yet)"
    fi
done

# 2. Copy resources
for skill in "${!SKILL_RESOURCES[@]}"; do
    src_path="${SKILL_RESOURCES[$skill]}"
    # Get just the resource dir name (e.g., "templates", "canvas-fonts", "themes")
    res_name=$(basename "$src_path")
    dest="$VENDOR_DIR/$skill/$res_name"
    if [ -d "$src_path" ]; then
        echo "  resource: $skill/$res_name → $dest/"
        mkdir -p "$dest"
        cp -r "$src_path"/* "$dest/"
    else
        echo "  resource: $skill/$res_name — not found in repo"
    fi
done

# 3. Copy SKILL.md files for reference
SKILLMD_DIR="$VENDOR_DIR/_skill-md"
mkdir -p "$SKILLMD_DIR"
for skill in "${ALL_SKILLS[@]}"; do
    src="skills/$skill/SKILL.md"
    if [ -f "$src" ]; then
        cp "$src" "$SKILLMD_DIR/$skill.md"
        echo "  SKILL.md: $skill"
    fi
done

# 4. Copy reference/examples directories
for skill in "${ALL_SKILLS[@]}"; do
    for subdir in reference examples; do
        src="skills/$skill/$subdir"
        if [ -d "$src" ]; then
            dest="$VENDOR_DIR/$skill/$subdir"
            mkdir -p "$dest"
            cp -r "$src"/* "$dest/"
            echo "  $subdir: $skill → $dest/"
        fi
    done
done

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "[CLEANUP] Removing temp clone ..."
rm -rf "$TEMP_DIR"

# Write marker
date -Iseconds > "$MARKER"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo ""
echo "[VERIFY] Checking key files ..."

verify_file() {
    if [ -f "$1" ]; then
        echo "  ✅ $2"
    else
        echo "  ❌ $2 — MISSING"
    fi
}

verify_dir() {
    if [ -d "$1" ]; then
        echo "  ✅ $2/"
    else
        echo "  ⚠️  $2/ — not found"
    fi
}

echo ""
echo "--- docx ---"
verify_file "$VENDOR_DIR/docx/office/unpack.py"     "docx/office/unpack.py"
verify_file "$VENDOR_DIR/docx/office/pack.py"        "docx/office/pack.py"
verify_file "$VENDOR_DIR/docx/office/validate.py"    "docx/office/validate.py"
verify_file "$VENDOR_DIR/docx/office/soffice.py"     "docx/office/soffice.py"
verify_file "$VENDOR_DIR/docx/accept_changes.py"     "docx/accept_changes.py"
verify_file "$VENDOR_DIR/docx/comment.py"            "docx/comment.py"
verify_dir  "$VENDOR_DIR/docx/office/validators"     "docx/office/validators"
verify_dir  "$VENDOR_DIR/docx/office/schemas"        "docx/office/schemas"

echo ""
echo "--- pdf ---"
verify_dir  "$VENDOR_DIR/pdf"                        "pdf"

echo ""
echo "--- pptx ---"
verify_dir  "$VENDOR_DIR/pptx"                       "pptx"
verify_file "$VENDOR_DIR/pptx/thumbnail.py"          "pptx/thumbnail.py"

echo ""
echo "--- xlsx ---"
verify_dir  "$VENDOR_DIR/xlsx"                       "xlsx"
verify_file "$VENDOR_DIR/xlsx/recalc.py"             "xlsx/recalc.py"

echo ""
echo "--- Resources ---"
verify_dir  "$VENDOR_DIR/algorithmic-art/templates"  "algorithmic-art/templates"
verify_dir  "$VENDOR_DIR/canvas-design/canvas-fonts" "canvas-design/canvas-fonts"
verify_dir  "$VENDOR_DIR/theme-factory/themes"       "theme-factory/themes"

echo ""
echo "--- SKILL.md Reference ---"
FOUND_MD=$(ls -1 "$SKILLMD_DIR"/*.md 2>/dev/null | wc -l)
echo "  Found $FOUND_MD SKILL.md files in $SKILLMD_DIR/"

echo ""
echo "============================================"
echo " Done."
echo ""
echo " Tool Valve SCRIPTS_DIR values:"
echo "   docx : $VENDOR_DIR/docx"
echo "   pdf  : $VENDOR_DIR/pdf"
echo "   pptx : $VENDOR_DIR/pptx"
echo "   xlsx : $VENDOR_DIR/xlsx"
echo "============================================"
