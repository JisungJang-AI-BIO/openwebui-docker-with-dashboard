# Installation Guide: OpenWebUI Skills

---

## Overview

This guide covers how to deploy OpenWebUI-Skills into an **OpenWebUI v0.8.8** environment.

### Key Concept: Skills vs Tools

| | Skills (Markdown) | Tools (Python) |
|---|---|---|
| **Format** | `.md` files with YAML frontmatter | `.py` files (Python class) |
| **Registration** | Workspace > Skills > Import | Workspace > Tools > Create |
| **Stored in** | OpenWebUI database | OpenWebUI database |
| **Execution** | Injected into system prompt (no code runs) | **Runs inside the OpenWebUI container** |
| **Dependencies** | None | System packages (apt) + Python packages (pip) |

**Skills need no container changes** — they are pure text stored in the database.

**Tools require dependencies installed inside the OpenWebUI container** — LibreOffice, Tesseract, Pandoc, Node.js, and various pip packages must exist in the same environment where OpenWebUI's Python runtime executes tool code.

---

## Scenario A: Existing OpenWebUI Container (Production)

You already have OpenWebUI running in Docker (e.g., `ghcr.io/open-webui/open-webui:cuda`).
The goal is to add document processing dependencies without disrupting your existing setup.

### Step 1: Clone This Repo on the Host

```bash
git clone https://github.com/JisungJang-AI-BIO/OpenWebUI-Skills.git
cd OpenWebUI-Skills
```

### Step 2: Build a Custom Image

The Dockerfile accepts a `BASE_IMAGE` build argument. Set it to match your current image:

```bash
# Match your current image tag (cuda, main, latest, etc.)
docker build --build-arg BASE_IMAGE=ghcr.io/open-webui/open-webui:cuda \
  -t openwebui-skills:cuda .
```

This builds a new image that is identical to your current one, plus:
- System packages: LibreOffice, Pandoc, Tesseract, Poppler, Node.js, Nanum fonts
- Python packages: python-docx, pypdf, reportlab, python-pptx, openpyxl, etc.
- Anthropic vendor scripts in `/app/OpenWebUI-Skills/vendor/`

### Step 3: Update Your docker-compose.yml

In your **existing** docker-compose.yml (the one that runs OpenWebUI), change the image:

```yaml
services:
  open-webui:
    # Before:
    # image: ghcr.io/open-webui/open-webui:cuda
    # After:
    image: openwebui-skills:cuda
    container_name: open-webui
    # ... rest of your config unchanged ...
```

Everything else stays the same — ports, volumes, env_file, GPU reservations, healthcheck, networks.

### Step 4: Recreate the Container

```bash
# In the directory with your docker-compose.yml
docker compose up -d
```

Docker will recreate the `open-webui` container with the new image.
The `open-webui-data` volume is preserved — no data loss.

### Step 5: Verify

```bash
docker exec open-webui bash -c "
  echo '=== LibreOffice ===' && soffice --version &&
  echo '=== Pandoc ===' && pandoc --version | head -1 &&
  echo '=== Tesseract ===' && tesseract --version 2>&1 | head -1 &&
  echo '=== Node.js ===' && node --version &&
  echo '=== python-docx ===' && python3 -c 'import docx; print(docx.__version__)' &&
  echo '=== pypdf ===' && python3 -c 'import pypdf; print(pypdf.__version__)' &&
  echo '=== Vendor scripts ===' && ls /app/OpenWebUI-Skills/vendor/
"
```

### Upgrading OpenWebUI Later

When a new OpenWebUI version is released:

```bash
# 1. Pull the new base image
docker pull ghcr.io/open-webui/open-webui:cuda

# 2. Rebuild the custom image on top
cd OpenWebUI-Skills && git pull
docker build --build-arg BASE_IMAGE=ghcr.io/open-webui/open-webui:cuda \
  -t openwebui-skills:cuda .

# 3. Recreate
cd /path/to/your/docker-compose && docker compose up -d
```

---

## Scenario B: Fresh Standalone Install

If you don't have OpenWebUI running yet and want a self-contained setup:

```bash
git clone https://github.com/JisungJang-AI-BIO/OpenWebUI-Skills.git
cd OpenWebUI-Skills

# Build (defaults to ghcr.io/open-webui/open-webui:main)
docker build -t openwebui-skills .

# Run
docker compose up -d
```

This uses the `docker-compose.yml` included in this repo.

---

## Scenario C: Runtime Install (Not Recommended)

If you cannot rebuild the image, you can install dependencies into a running container.
**These changes are lost when the container is recreated.**

```bash
# Shell into the running container
docker exec -it open-webui bash

# Install system dependencies
apt-get update && apt-get install -y --no-install-recommends \
  libreoffice pandoc poppler-utils qpdf \
  tesseract-ocr tesseract-ocr-kor \
  nodejs npm fonts-nanum fonts-nanum-coding fonts-nanum-extra git
fc-cache -fv
npm install -g docx

# Clone vendor scripts
cd /app && git clone --depth 1 https://github.com/JisungJang-AI-BIO/OpenWebUI-Skills.git
cd OpenWebUI-Skills && bash server-setup/clone-anthropic-scripts.sh

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt
```

> **Warning**: All of the above is lost on `docker compose up -d` (container recreate).
> To persist, commit the container: `docker commit open-webui openwebui-skills:cuda`

---

## Registering Skills & Tools in OpenWebUI (v0.8+)

### Automated Import (Recommended)

```bash
bash scripts/import-skills-tools.sh                     # production
bash scripts/import-skills-tools.sh open-webui-staging  # staging
```

No API key needed — the script runs inside the container and inserts directly into the database. It is also called automatically by `setup.sh` and `clone-db-to-staging.sh`. Requires at least one admin account to exist.

### Manual Import (Alternative)

If you prefer to register manually via the web UI:

### Skills (Markdown → Workspace > Skills)

Skills are markdown instructions injected into the model's system prompt.

1. Go to **Workspace > Skills**
2. Click **Import** and select `.md` files from `skills/` directory
3. Each file has YAML frontmatter — `name` and `description` are auto-populated
4. Toggle each skill **Active**

### Tools (Python → Workspace > Tools)

Tools are Python executables that give models function-calling capabilities.

1. Go to **Workspace > Tools**
2. Click **+** (Create new tool)
3. Paste the full contents of a `tools/*.py` file
4. Save, then click the **gear icon** to configure Valves

### Attach to Models

1. Go to **Workspace > Models**, select (or create) a model
2. In the **Skills** section, check the skills to attach
3. In the **Tools** section, check the tools to enable
4. Save

**Skill loading is token-efficient**: model-attached skills inject only a manifest (name + description). The model loads full instructions on-demand via the built-in `view_skill` tool.

---

## Tool Valve Configuration

After registering tools, configure Valves (gear icon on each tool).

For the custom image, vendor scripts are at:
```
/app/OpenWebUI-Skills/vendor/{docx,pdf,pptx,xlsx}
```

### All Valves by Tool

**docx_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `SCRIPTS_DIR` | *(must set)* | `/app/OpenWebUI-Skills/vendor/docx` |
| `TEMP_DIR` | `/tmp/openwebui-docx` | default OK |
| `LIBREOFFICE_PATH` | `soffice` | default OK |
| `PANDOC_PATH` | `pandoc` | default OK |
| `NODE_PATH` | `node` | default OK |
| `USE_DOCXJS` | `True` | default OK |
| `DEFAULT_FONT` | `Arial` | `NanumGothic` for Korean-first |

**pdf_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `TEMP_DIR` | `/tmp/openwebui-pdf` | default OK |
| `LIBREOFFICE_PATH` | `soffice` | default OK |
| `TESSERACT_PATH` | `tesseract` | default OK |
| `TESSERACT_LANG` | `eng+kor` | default OK |
| `POPPLER_PATH` | *(empty = system)* | default OK |

**pptx_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `SCRIPTS_DIR` | *(must set)* | `/app/OpenWebUI-Skills/vendor/pptx` |
| `TEMP_DIR` | `/tmp/openwebui-pptx` | default OK |
| `LIBREOFFICE_PATH` | `soffice` | default OK |
| `DEFAULT_FONT` | `Arial` | `NanumGothic` for Korean-first |

**xlsx_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `SCRIPTS_DIR` | *(must set)* | `/app/OpenWebUI-Skills/vendor/xlsx` |
| `TEMP_DIR` | `/tmp/openwebui-xlsx` | default OK |
| `LIBREOFFICE_PATH` | `soffice` | default OK |

**gif_creator_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `TEMP_DIR` | `/tmp/openwebui-gif` | default OK |
| `MAX_WIDTH` | `480` | default OK |
| `MAX_HEIGHT` | `480` | default OK |
| `MAX_FPS` | `30` | default OK |
| `MAX_FRAMES` | `120` | default OK |

**webapp_testing_tool.py**

| Valve | Default | Production Value |
|-------|---------|-----------------|
| `TEMP_DIR` | `/tmp/openwebui-webtest` | default OK |
| `TIMEOUT` | `30000` | default OK |
| `HEADLESS` | `True` | default OK |
| `BROWSER` | `chromium` | default OK |

---

## System Dependencies (apt)

All installed automatically by the Dockerfile. For manual installs:

```bash
bash server-setup/install-system-deps.sh
```

| Package | Purpose |
|---------|---------|
| **LibreOffice** | Document conversion (docx→pdf, tracked changes, formula recalc) |
| **Pandoc** | Format conversion (docx→html/md/txt) |
| **Poppler** (pdftoppm) | PDF→image conversion |
| **qpdf** | PDF utilities |
| **Tesseract OCR** + kor | Scanned PDF text recognition |
| **Node.js** + npm | docx-js document creation |
| **docx** (npm) | Node.js DOCX library |
| **Nanum fonts** | Korean font rendering |

---

## Python Dependencies (pip)

All installed automatically by the Dockerfile. For manual installs:

```bash
bash server-setup/install-python-deps.sh --phase all
```

| Phase | Packages | Command |
|-------|----------|---------|
| `docx` | python-docx, lxml, mammoth, defusedxml | `--phase docx` |
| `pdf` | pypdf, pdfplumber, reportlab, pdf2image, pytesseract, Pillow | `--phase pdf` |
| `office` | python-pptx, openpyxl, pandas, xlsxwriter | `--phase office` |
| `1` | All of the above (docx + pdf + office) | `--phase 1` |
| `2` | imageio, numpy (GIF creator) | `--phase 2` |
| `3` | playwright (web testing) | `--phase 3` |
| `all` | Everything | `--phase all` |

---

## Package Role Reference

| Package | Purpose | System Dep |
|---------|--------|------------|
| `python-docx` | .docx read/write/edit | — |
| `lxml` | XML parsing | libxml2-dev (usually pre-installed) |
| `mammoth` | DOCX → HTML | — |
| `defusedxml` | Secure XML parsing | — |
| `pypdf` | PDF read/write/merge/split/encrypt | — |
| `pdfplumber` | PDF text/table extraction | — |
| `reportlab` | PDF creation | — |
| `pdf2image` | PDF → image | poppler-utils (apt) |
| `pytesseract` | OCR | tesseract-ocr (apt) |
| `Pillow` | Image processing | — |
| `python-pptx` | .pptx read/write/edit | — |
| `openpyxl` | .xlsx read/write | — |
| `pandas` | Tabular data | — |
| `xlsxwriter` | .xlsx creation with charts | — |
