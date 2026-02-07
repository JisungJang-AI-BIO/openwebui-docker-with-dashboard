# Open WebUI Dashboard (WSL Development Environment)

This project provides a development environment for an Open WebUI dashboard that mirrors a production on-premise setup.

## Prerequisites
- Windows with WSL 2 enabled.
- Ubuntu installed in WSL.
- Docker Desktop for Windows (configured to work with WSL 2).

## Setup Instructions

### 1. Configure Environment Variables
Copy the example environment file and fill in your secrets:
```bash
cp .env.example .env
# Edit .env and set your passwords and secrets
```

### 2. Setup Conda Environment (WSL)
Run the setup script inside your WSL terminal:
```bash
# In WSL terminal, navigate to the project directory:
cd /mnt/d/openwebui-dashboard
bash setup_env.sh
```
This will:
- Install Miniforge (if not present) to `/mnt/d/miniforge3`.
- Create a `openwebui` conda environment with Python 3.11.
- Install `open-webui[all]`.

## Integration Guide (Existing Environment)

If you already have Open WebUI and PostgreSQL running in your environment:

1.  **Configure Environment**:
    - Ensure your `.env` file contains the correct database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) and `POSTGRES_HOST`.
    - If running on the same machine but outside Docker, `POSTGRES_HOST` should be `localhost`.
    - If running in Docker, you might need to connect to the existing network.

2.  **Run Dashboard**:
    Navigate to the `dashboard` directory and run:
    ```bash
    cd dashboard
    docker-compose up -d --build
    ```

3.  **Access**:
    Open your browser and navigate to `http://localhost:8501`.

## Development Setup (From Scratch)

1.  **Environment Setup**:
    - Run `bash setup_env.sh` to install Miniforge and create the Conda environment.
    - Activate the environment: `conda activate openwebui`.

2.  **Database**:
    - Start the PostgreSQL container: `docker-compose up -d postgres`.

3.  **Run Dashboard**:
    - Navigate to `dashboard/` and run `streamlit run app.py`.

### 3. Start Database
Start the PostgreSQL + pgvector database using Docker Compose:
```bash
docker-compose up -d postgres
```

### 4. Run Open WebUI (Optional)
To populate the database with initial data, you can run Open WebUI:
```bash
conda activate openwebui
# Ensure env vars are set or exported
export POSTGRES_DB=openwebui
export POSTGRES_USER=openwebui_admin
export POSTGRES_PASSWORD=your_password
# ... export other vars ...
open-webui serve
```
*Note: Make sure Open WebUI is configured to use the PostgreSQL database running in Docker.*

### 5. Run Dashboard
Start the dashboard application:
```bash
conda activate openwebui
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```
Open your browser to `http://localhost:8501`.

## Project Structure
- `planning.md`: detailed project plan.
- `setup_env.sh`: Automated environment setup script.
- `docker-compose.yml`: Database configuration.
- `dashboard/`: Dashboard source code.
