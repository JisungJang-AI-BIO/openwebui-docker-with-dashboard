# Open WebUI Dashboard

Analytics dashboard for Open WebUI — connects to the existing PostgreSQL database and visualizes chat usage, model statistics, and feedback data.

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

- **Overview Stats**: Total chats, messages, models used, feedbacks
- **Daily Usage Chart**: Bar chart with from/to date range picker (KST)
- **Model Usage**: Pie chart by model, average response length comparison
- **Recent Chats**: Sortable table with title, model, message count, timestamps
- **Feedback Summary**: Positive/negative ratio and recent feedback list

## Quick Start

### Prerequisites

- Docker & Docker Compose
- `.env` file with database credentials (see `.env.example` or below)

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Database health check |
| GET | `/api/stats/overview` | Total chats, messages, models, feedbacks |
| GET | `/api/stats/daily?from=YYYY-MM-DD&to=YYYY-MM-DD` | Daily usage (KST dates) |
| GET | `/api/stats/models` | Model usage count and avg response length |
| GET | `/api/chats/recent?limit=20` | Recent chat list |
| GET | `/api/feedbacks/summary` | Feedback positive/negative + recent list |

## Port Configuration

| Service | Host Port | Internal Port | Description |
|---------|-----------|---------------|-------------|
| PostgreSQL | 5435 | 5432 | Open WebUI database |
| Backend (FastAPI) | 8005 | 8000 | Dashboard API server |
| Frontend (React) | 3005 | 5173 | Dashboard UI |

> **Note**: Port 5432 is reserved for the production PostgreSQL instance.

## Production Deployment

This project is fully containerized. To deploy on a production server:

```bash
git clone <repo-url>
cd openwebui-dashboard
cp .env.example .env   # configure with production DB credentials
docker compose up --build -d
```

For production, point `POSTGRES_HOST` to the existing Open WebUI PostgreSQL instance instead of the local container.

## Development (Local Open WebUI)

To generate test chat data locally:

```bash
# Start only the database
docker compose up -d postgres

# Run Open WebUI via conda
bash start_openwebui.sh
# Open WebUI available at http://localhost:30072
```

## Project Structure

```
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py          # FastAPI endpoints
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.tsx           # Root component
│       ├── lib/api.ts        # API client (axios)
│       ├── components/       # Reusable UI components
│       └── pages/            # Dashboard page
├── docker-compose.yml
├── .env
├── backup_db.sh              # One-click DB backup script
└── docs/
    └── postgresql-backup-guide.md
```

## Database Backup

```bash
bash backup_db.sh
```

See `docs/postgresql-backup-guide.md` for detailed backup/restore instructions.
