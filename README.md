# Open WebUI Docker with Dashboard

Docker Compose deployment for [Open WebUI](https://github.com/open-webui/open-webui) with OKTA OIDC SSO, NVIDIA GPU support, and an integrated analytics dashboard — all connecting to a shared PostgreSQL (pgvector) database.

## Architecture

```
                     Internet
                        │
                   ┌────┴────┐
                   │  nginx  │
                   └────┬────┘
            ┌───────────┼───────────┐
        :443│       :443│       :30088
            │           │           │
     ┌──────┴──────┐    │    ┌──────┴──────┐
     │  /ws/ (WS)  │    │    │  /api/ → :10086 (backend)
     │  / (HTTP)   │    │    │  /     → :10087 (frontend)
     └──────┬──────┘    │    └──────┬──────┘
            │           │           │
            ▼           │           ▼
     ┌─────────────┐    │    ┌─────────────┐  ┌─────────────┐
     │  Open WebUI │    │    │  Dashboard  │  │  Dashboard  │
     │  :10085     │    │    │  Backend    │  │  Frontend   │
     │  (CUDA+SSO) │    │    │  FastAPI    │  │  React+nginx│
     └──────┬──────┘    │    │  :10086     │  │  :10087     │
            │           │    └──────┬──────┘  └─────────────┘
            │           │           │
            └───────────┼───────────┘
                        │
              ┌─────────┴─────────┐
              │     webui-db      │
              │  PostgreSQL 18    │
              │  + pgvector       │
              │  (external)       │
              └───────────────────┘
```

All services join the pre-existing `openwebui-db_default` Docker network where the `webui-db` PostgreSQL container is running.

## Services

| Service | Container | Image / Build | Host Port | Description |
|---------|-----------|--------------|-----------|-------------|
| Open WebUI | `open-webui` | `ghcr.io/open-webui/open-webui:cuda` | 10085 | LLM chat UI with OKTA SSO and GPU inference |
| Dashboard Backend | `dashboard-backend` | `./dashboard/backend` (FastAPI) | 10086 | Analytics API — reads Open WebUI tables |
| Dashboard Frontend | `dashboard-frontend` | `./dashboard/frontend` (React → nginx) | 10087 | Analytics UI — served as static build |

All host ports bind to `127.0.0.1` only. External access is handled by the host nginx reverse proxy.

## Dashboard Features

- **Overview Stats** — total chats, messages, workspaces, feedbacks
- **Daily Usage Chart** — line chart with date range picker (KST)
- **Workspace Ranking** — chat/message/user counts, feedback rating per workspace
- **Developer Ranking** — aggregated metrics per workspace developer
- **Group Ranking** — team usage metrics with per-member averages
- **Python Package Requests** — users request packages, admins manage status (pending/installed/rejected/uninstalled), export as `requirements.txt`

## Prerequisites

- Docker 20.10+ with Compose V2
- NVIDIA Container Toolkit (for GPU passthrough)
- A running `webui-db` PostgreSQL container on the `openwebui-db_default` network
- nginx (host-level reverse proxy)

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/JisungJang-AI-BIO/openwebui-docker-with-dashboard.git
cd openwebui-docker-with-dashboard
cp .env.example .env
chmod 600 .env
```

Edit `.env` and fill in:
- `DB_PASSWORD` — PostgreSQL password (also update the connection strings)
- `OAUTH_CLIENT_SECRET` — OKTA production client secret (uncomment the line)
- `WEBUI_SECRET_KEY` — generate with `openssl rand -hex 32` (uncomment the line)

### 2. Deploy

```bash
bash scripts/setup.sh
```

The setup script will:
1. Verify Docker, Compose, GPU, and the `openwebui-db_default` network
2. Generate `WEBUI_SECRET_KEY` if not set
3. Build dashboard images and pull the Open WebUI CUDA image
4. Start all services and run health checks

### 3. Configure nginx

Copy the provided nginx config and reload:

```bash
sudo cp nginx/openwebui.conf /etc/nginx/conf.d/openwebui.conf
sudo nginx -t && sudo systemctl reload nginx
```

Ensure port **30088** is open in the firewall for dashboard access.

### 4. Verify

```bash
curl http://127.0.0.1:10085/health     # Open WebUI
curl http://127.0.0.1:10086/health     # Dashboard backend
docker exec open-webui nvidia-smi      # GPU
```

Access URLs:
- **Open WebUI**: `https://openwebui.sbiologics.com`
- **Dashboard**: `https://openwebui.sbiologics.com:30088`

## Project Structure

```
openwebui-docker-with-dashboard/
├── docker-compose.yml          # 3 services: open-webui, dashboard-backend, dashboard-frontend
├── .env.example                # Environment template (secrets redacted)
├── .dockerignore
├── dashboard/
│   ├── backend/
│   │   ├── Dockerfile          # Python 3.11 + FastAPI
│   │   ├── requirements.txt
│   │   └── app/
│   │       └── main.py         # API endpoints, DB queries, auth
│   └── frontend/
│       ├── Dockerfile          # Multi-stage: node build → nginx serve
│       ├── nginx.conf          # SPA fallback config
│       ├── package.json
│       └── src/
│           ├── App.tsx
│           ├── lib/
│           │   ├── api.ts      # Axios client (same-origin in production)
│           │   └── utils.ts
│           ├── components/
│           │   ├── Layout.tsx
│           │   ├── StatCard.tsx
│           │   ├── DailyChart.tsx
│           │   ├── WorkspaceRankingTable.tsx
│           │   ├── DeveloperRankingTable.tsx
│           │   ├── GroupRankingTable.tsx
│           │   ├── RequirePackages.tsx
│           │   └── MockAuthBanner.tsx
│           └── pages/
│               └── Dashboard.tsx
├── nginx/
│   └── openwebui.conf          # Host nginx: 443 (WebUI) + 30088 (Dashboard)
├── scripts/
│   ├── setup.sh                # Automated deployment script
│   └── backup_db.sh            # PostgreSQL backup with 7-day retention
└── docs/
    ├── postgresql-backup-guide.md
    ├── sso-integration-guide.md
    └── development-sop.md
```

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_USER` | `webui_user` | PostgreSQL username |
| `DB_PASSWORD` | — | PostgreSQL password |
| `DB_HOST` | `webui-db` | PostgreSQL container hostname |
| `DATABASE_URL` | — | Full connection string for Open WebUI |
| `WEBUI_SECRET_KEY` | — | Session signing key (required for persistent sessions) |
| `OAUTH_CLIENT_ID` | — | OKTA OIDC client ID |
| `OAUTH_CLIENT_SECRET` | — | OKTA OIDC client secret |
| `ENABLE_LOGIN_FORM` | `true` | Set to `false` after SSO is verified |
| `OPENWEBUI_PORT` | `10085` | Open WebUI host port |
| `DASHBOARD_BACKEND_PORT` | `10086` | Dashboard API host port |
| `DASHBOARD_FRONTEND_PORT` | `10087` | Dashboard UI host port |
| `DASHBOARD_AUTH_MODE` | `mock` | `mock` for dev, `sso` for production |
| `DASHBOARD_ADMIN_USERS` | `jisung.jang` | Comma-separated admin usernames |
| `GLOBAL_LOG_LEVEL` | `DEBUG` | Open WebUI log level |

See [.env.example](.env.example) for the full list with comments.

### Networking

All three services connect to the **external** Docker network `openwebui-db_default`, which is managed by the separate `webui-db` PostgreSQL stack. This eliminates any need for `extra_hosts` or PostgreSQL configuration changes — containers resolve `webui-db` by container name on the shared network.

### nginx (Host Reverse Proxy)

| Port | Service | Upstream |
|------|---------|----------|
| 443 | Open WebUI | `127.0.0.1:10085` (with WebSocket support for `/ws/`) |
| 30088 | Dashboard API | `127.0.0.1:10086` (path prefix `/api/`) |
| 30088 | Dashboard UI | `127.0.0.1:10087` (everything else) |

Both ports use TLS 1.3 with a wildcard certificate.

## Dashboard API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Database health check |
| GET | `/api/stats/overview` | No | Total chats, messages, models, feedbacks |
| GET | `/api/stats/daily?from=&to=` | No | Daily usage (KST dates) |
| GET | `/api/stats/workspace-ranking` | No | Workspace metrics with feedback rating |
| GET | `/api/stats/developer-ranking` | No | Developer aggregated metrics |
| GET | `/api/stats/group-ranking` | No | Group metrics with per-member averages |
| GET | `/api/auth/me` | Yes | Current user info + admin flag |
| GET | `/api/packages` | No | List all requested packages |
| POST | `/api/packages` | Yes | Request a new package |
| DELETE | `/api/packages/{id}` | Yes | Delete own request (or admin) |
| PATCH | `/api/packages/{id}/status` | Admin | Change package status |

## Operations

### Backup

```bash
bash scripts/backup_db.sh
```

Creates a compressed dump in `./backups/` with automatic cleanup of backups older than 7 days. See [docs/postgresql-backup-guide.md](docs/postgresql-backup-guide.md) for restore instructions.

### Update

```bash
docker compose pull              # Pull latest Open WebUI image
docker compose build             # Rebuild dashboard images
docker compose up -d             # Recreate changed containers
```

Named volumes (`open-webui-data`) are preserved across updates.

### Logs

```bash
docker compose logs -f                      # All services
docker compose logs -f open-webui           # Open WebUI only
docker compose logs -f dashboard-backend    # Dashboard API only
```

### Restart / Stop

```bash
docker compose restart           # Restart all services
docker compose down              # Stop and remove containers
```

**Never use `docker compose down -v`** — the `-v` flag deletes named volumes and causes permanent data loss.

## Rollback

All rollback targets the current deployment (port 10085). The previous conda-based services remain independent.

1. **Config issue**: edit `.env`, then `docker compose up -d`
2. **Container issue**: `docker compose down && docker compose up -d`
3. **Image issue**: pin a previous image tag in `docker-compose.yml`, then pull and recreate
4. **Full teardown**: `docker compose down && docker volume rm open-webui-data`

## Firewall Requirements

| Destination | Port | Purpose |
|-------------|------|---------|
| `ghcr.io` | 443 | Open WebUI Docker image registry |
| `pkg-containers.githubusercontent.com` | 443 | Image layer downloads |
| `*.blob.core.windows.net` | 443 | Image layer storage (Azure) |
| Inbound `30088` | TCP | Dashboard web access |

## Documentation

- [docs/postgresql-backup-guide.md](docs/postgresql-backup-guide.md) — DB backup/restore guide
- [docs/sso-integration-guide.md](docs/sso-integration-guide.md) — OKTA SSO integration guide
- [docs/development-sop.md](docs/development-sop.md) — Development standard operating procedure
