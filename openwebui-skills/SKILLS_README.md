# OpenWebUI-Skills

Anthropic [Skills](https://github.com/anthropics/skills) (16 types) ported for on-premise **OpenWebUI v0.8.8** environments.

## What This Is

Anthropic publishes Skills — markdown prompts paired with bash/python scripts — designed for Claude Code. This project converts them into **OpenWebUI Skills** (system prompt text) and **OpenWebUI Tools** (Python function-calling executables) so they work with any LLM served via OpenWebUI.

```
Anthropic Skill (SKILL.md + scripts/)
        │
        ▼  porting
┌───────────────────┐    ┌────────────────────┐
│  OpenWebUI Skill  │    │  OpenWebUI Tool     │
│  (Markdown text)  │    │  (Python class)     │
│  → system prompt  │    │  → function calling │
└───────────────────┘    └────────────────────┘
```

## Target Infrastructure

| Component | Detail |
|-----------|--------|
| OpenWebUI | v0.8.8, Ubuntu, Docker container (`ghcr.io/open-webui/open-webui:cuda`) |
| LLM | vLLM: Qwen3-235B, GPT-OSS-120B, Qwen3.5-397B (planned) |
| Embedding | Ollama: qwen3-embedding, bge-m3 |

## Repository Structure

```
OpenWebUI-Skills/
├── Dockerfile                 # Custom image (extends official OpenWebUI)
├── docker-compose.yml         # One-command deployment
│
├── tools/                     # OpenWebUI Tool — Python executables
│   ├── docx_tool.py           #   Word document read/create/edit/convert
│   ├── pdf_tool.py            #   PDF read/create/merge/split/OCR/protect
│   ├── pptx_tool.py           #   PowerPoint read/create/edit/convert
│   ├── xlsx_tool.py           #   Excel read/create/edit/recalculate
│   ├── gif_creator_tool.py    #   Animated GIF creation (Slack emoji/message)
│   └── webapp_testing_tool.py #   Playwright-based web testing & screenshots
│
├── skills/                    # OpenWebUI Skill — Markdown prompt text (16 files)
│   ├── docx.md                #   DOCX workflow guide
│   ├── pdf.md                 #   PDF workflow guide
│   ├── pptx.md                #   PPTX workflow guide
│   ├── xlsx.md                #   XLSX workflow guide
│   ├── webapp-testing.md      #   Web testing workflow guide
│   └── ... (11 more)          #   Design, comms, art, builder skills
│
├── vendor/                    # Anthropic original scripts (cloned at build)
│   ├── docx/                  #   office/unpack.py, pack.py, validate.py, ...
│   ├── pdf/                   #   PDF processing scripts
│   ├── pptx/                  #   Presentation scripts
│   └── xlsx/                  #   Spreadsheet scripts
│
├── server-setup/              # Automated setup (used in Dockerfile)
│   ├── setup.sh               #   Master orchestrator
│   ├── install-system-deps.sh #   apt packages
│   ├── install-python-deps.sh #   pip packages (--phase docx|pdf|1|all)
│   ├── clone-anthropic-scripts.sh  # Sparse-clone scripts → vendor/
│   └── verify-all.sh          #   Full environment validation
│
├── tests/                     # Test guides and scripts
├── PORTING_PLAN.md            # Master plan (all 16 skills)
├── DESIGN_DECISIONS.md        # Architecture rationale
├── INSTALLATION_GUIDE.md      # Step-by-step server setup
└── requirements.txt           # Python dependencies
```

## All 16 Skills — Porting Status

| # | Skill | Type | Status |
|---|-------|------|--------|
| 1 | **docx** | Tool + Skill | **Done** |
| 2 | **pdf** | Tool + Skill | **Done** |
| 3 | **pptx** | Tool + Skill | **Done** |
| 4 | **xlsx** | Tool + Skill | **Done** |
| 5 | **doc-coauthoring** | Skill Only | **Done** |
| 6 | **internal-comms** | Skill Only | **Done** |
| 7 | **mcp-builder** | Skill Only | **Done** |
| 8 | **skill-creator** | Skill Only | **Done** |
| 9 | **brand-guidelines** | Skill Only | **Done** |
| 10 | **theme-factory** | Skill Only | **Done** |
| 11 | **frontend-design** | Skill Only | **Done** |
| 12 | **canvas-design** | Skill Only | **Done** |
| 13 | **algorithmic-art** | Skill Only | **Done** |
| 14 | **web-artifacts-builder** | Skill Only | **Done** |
| 15 | **slack-gif-creator** | Tool Only | **Done** |
| 16 | **webapp-testing** | Tool + Skill | **Done** |

## Quick Start

### Adding to an Existing OpenWebUI Container (Production)

If you already have OpenWebUI running in Docker (e.g., `ghcr.io/open-webui/open-webui:cuda`):

```bash
# 1. Clone this repo on the host
git clone https://github.com/JisungJang-AI-BIO/OpenWebUI-Skills.git

# 2. Build a custom image that extends your current base
cd OpenWebUI-Skills
docker build --build-arg BASE_IMAGE=ghcr.io/open-webui/open-webui:cuda \
  -t openwebui-skills:cuda .

# 3. Update your docker-compose.yml to use the new image
#    image: ghcr.io/open-webui/open-webui:cuda
#    →  image: openwebui-skills:cuda

# 4. Recreate the container (data volume is preserved)
docker compose up -d
```

> **Why a custom image?** Tools (Python) execute inside OpenWebUI's runtime.
> System packages (LibreOffice, Tesseract, etc.) and pip packages must exist
> inside the container. A custom image bakes these in so they survive restarts.

### Fresh Install (Standalone)

```bash
git clone https://github.com/JisungJang-AI-BIO/OpenWebUI-Skills.git
cd OpenWebUI-Skills
docker build -t openwebui-skills .
docker compose up -d
```

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for the full step-by-step guide.

## Importing into OpenWebUI (v0.8+)

OpenWebUI v0.8+ has a dedicated **Workspace > Skills** section. Skills (markdown) and Tools (Python) are registered separately.

### Step 1: Register Skills (Markdown)

**Workspace > Skills > Import**

Each `skills/*.md` file includes YAML frontmatter (`name`, `description`) and can be imported directly:

1. Go to **Workspace > Skills**
2. Click **Import** and select `.md` files from `skills/` directory
3. Toggle each skill **Active**

Or use the automated import script (no API key needed):
```bash
bash scripts/import-skills-tools.sh                     # production
bash scripts/import-skills-tools.sh open-webui-staging  # staging
```

This runs inside the container and inserts directly into the database. It is also called automatically by `setup.sh` and `clone-db-to-staging.sh`.

### Step 2: Register Tools (Python)

**Workspace > Tools > + (Create)**

Each `tools/*.py` file is a standalone Tool:

1. Go to **Workspace > Tools**
2. Click **+** (Create new tool)
3. Paste the contents of a `tools/*.py` file
4. Save
5. Click the gear icon to configure **Valves** (paths, limits)

| Tool File | Valves to Configure |
|-----------|-------------------|
| `docx_tool.py` | `SCRIPTS_DIR` → vendor/docx path |
| `pdf_tool.py` | `TESSERACT_PATH`, `POPPLER_PATH` |
| `pptx_tool.py` | `SCRIPTS_DIR` → vendor/pptx path |
| `xlsx_tool.py` | `SCRIPTS_DIR` → vendor/xlsx path |
| `gif_creator_tool.py` | defaults OK |
| `webapp_testing_tool.py` | `BROWSER` (chromium/firefox) |

### Step 3: Attach to Models

**Workspace > Models > Edit > Skills / Tools**

1. Go to **Workspace > Models**, select (or create) a model
2. In the **Skills** section, check the skills to attach
3. In the **Tools** section, check the tools to enable
4. Save

**How skill loading works:**
- Model-attached skills inject only a lightweight **manifest** (name + description) into the system prompt
- The model receives a built-in `view_skill` tool and loads full instructions **on-demand** — token-efficient even with many skills attached
- Users can also invoke skills ad-hoc in chat with the `$` prefix (e.g., `$docx`)

### Recommended Model Presets

| Preset | Skills | Tools |
|--------|--------|-------|
| Document Worker | docx, pdf, pptx, xlsx, doc-coauthoring, internal-comms | docx, pdf, pptx, xlsx |
| Designer | frontend-design, canvas-design, brand-guidelines, theme-factory, algorithmic-art | gif-creator |
| Developer | mcp-builder, skill-creator, web-artifacts-builder, webapp-testing | webapp-testing |
| All-in-One | all 16 | all 6 |

## Design Approach

**Hybrid architecture** — original Anthropic scripts are used as-is via subprocess, not rewritten:

- **Reading**: `python-docx` (pure Python, no subprocess)
- **Creation**: `docx-js` via Node.js subprocess (Anthropic's reference implementation) with `python-docx` fallback
- **XML Editing**: Anthropic's `unpack.py`/`pack.py` via subprocess, with fallback if scripts unavailable
- **Conversion**: LibreOffice / Pandoc via subprocess
- **Validation**: Anthropic's `validate.py` via subprocess, with basic structural validation fallback

See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for full rationale.

## Documentation

| Document | Purpose |
|----------|---------|
| [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) | Server setup step-by-step |
| [PORTING_PLAN.md](PORTING_PLAN.md) | Master plan for all 16 skills |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | Architecture decisions |
| [tests/TEST_GUIDE.md](tests/TEST_GUIDE.md) | Testing guide for Ubuntu server |

## License

MIT
