# SbioChat Dashboard

Analytics dashboard for Open WebUI — connects to the existing PostgreSQL database and visualizes chat usage, workspace/developer/group rankings, and manages Python package requests.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL   │
│  React + TS  │     │   FastAPI    │     │  (pgvector)   │
│  port 3005   │     │  port 8005   │     │  port 5435    │
└──────────────┘     └──────────────┘     └──────────────┘
```

All services run as Docker containers via `docker-compose.yml`.

## Features

- **Overview Stats**: Total chats, messages, workspaces, feedbacks
- **Daily Usage Chart**: Line chart with date range picker (KST)
- **Workspace Ranking**: Chat/message/user counts, feedback rating per workspace
- **Developer Ranking**: Aggregated metrics per workspace developer
- **Group Ranking**: Team usage metrics with per-member averages
- **Require Python Packages**: Users request packages, admin manages install status (pending/installed/rejected/uninstalled), export as requirements.txt
- **Mock Auth**: Development-mode user switching via `X-Auth-User` header (SSO-ready)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- `.env` file with database credentials (see below)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

Required variables:
```
POSTGRES_DB=openwebui
POSTGRES_USER=openwebui_admin
POSTGRES_PASSWORD=<your_password>
POSTGRES_PORT_INTERNAL=5432
POSTGRES_PORT_HOST=5435
BACKEND_PORT_INTERNAL=8000
BACKEND_PORT_HOST=8005
FRONTEND_PORT_INTERNAL=5173
FRONTEND_PORT_HOST=3005
AUTH_MODE=mock
ADMIN_USERS=jisung.jang
```

### 2. Build & Run

```bash
docker compose up --build -d
```

### 3. Access

- **Dashboard**: http://localhost:3005
- **API**: http://localhost:8005
- **API Docs**: http://localhost:8005/docs

## API Endpoints

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

## Authentication

### Development (Mock Auth)
- `AUTH_MODE=mock` in `.env`
- Frontend shows a Dev Mode banner (bottom-right) to switch mock users
- Backend reads `X-Auth-User` header for identity
- Only `@samsung.com` email prefixes are accepted

### Production (SSO)
- `AUTH_MODE=sso` in `.env`
- Knox Portal (IdP) → Keycloak (SAML 2.0) → Dashboard (OIDC 2.0)
- See `docs/sso-integration-guide.md` for setup instructions

## Port Configuration

| Service | Host Port | Internal Port | Description |
|---------|-----------|---------------|-------------|
| PostgreSQL | 5435 | 5432 | Open WebUI database |
| Backend (FastAPI) | 8005 | 8000 | Dashboard API server |
| Frontend (React) | 3005 | 5173 | Dashboard UI |

> **Note**: Port 5432 is reserved for the production PostgreSQL instance.

## Project Structure

```
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py              # FastAPI endpoints + auth
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── lib/
│       │   ├── api.ts           # API client (axios) + types
│       │   └── utils.ts
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── StatCard.tsx
│       │   ├── DailyChart.tsx
│       │   ├── WorkspaceRankingTable.tsx
│       │   ├── DeveloperRankingTable.tsx
│       │   ├── GroupRankingTable.tsx
│       │   ├── RequirePackages.tsx  # Package request management
│       │   └── MockAuthBanner.tsx   # Dev-mode auth switcher
│       └── pages/
│           └── Dashboard.tsx
├── docker-compose.yml
├── .env
├── backup_db.sh
└── docs/
    ├── postgresql-backup-guide.md
    ├── sso-integration-guide.md
    └── development-sop.md
```

## Database

### Custom Tables

The `python_packages` table is auto-created on backend startup:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| package_name | VARCHAR(255) UNIQUE | Python package name |
| added_by | VARCHAR(255) | Email prefix of requester |
| added_at | TIMESTAMPTZ | Request timestamp |
| status | VARCHAR(20) | pending / installed / rejected / uninstalled |
| status_note | TEXT | Optional admin note |
| status_updated_by | VARCHAR(255) | Admin who changed status |
| status_updated_at | TIMESTAMPTZ | Status change timestamp |

### Backup

```bash
bash backup_db.sh
```

See `docs/postgresql-backup-guide.md` for detailed backup/restore instructions.

## Development

### Hot Reload

Both backend and frontend support hot reload via Docker volume mounts:
- Backend: `./backend/app` → `/app/app` (uvicorn `--reload`)
- Frontend: `./frontend/src` → `/app/src` (Vite HMR)

Source file changes are reflected immediately without `docker compose --build`.

### Local Open WebUI (Test Data)

```bash
# Start only the database
docker compose up -d postgres

# Run Open WebUI via conda
bash start_openwebui.sh
# Open WebUI available at http://localhost:30072
```

## Documentation

- `docs/postgresql-backup-guide.md` — DB backup/restore guide
- `docs/sso-integration-guide.md` — Knox Portal SSO integration guide
- `docs/development-sop.md` — Development standard operation protocol
