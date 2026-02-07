#!/bin/bash

# Load secrets from .env automatically if present
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Loaded .env file"
fi

# This script assumes you are running on the HOST (WSL), connecting to the Dockerized DB.

# 1. Database Configuration (Connecting to Docker container from Host)
# Override specific vars for Host access
export POSTGRES_USER=openwebui_admin
export POSTGRES_PASSWORD=AIteam_2026  # Update this or load from .env
export POSTGRES_DB=openwebui
export POSTGRES_HOST=localhost
export POSTGRES_PORT=${POSTGRES_PORT_HOST}

# Construct DATABASE_URL for Open WebUI (Peewee/SQLAlchemy)
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# 2. Vector DB Configuration
export VECTOR_DB=pgvector

# 3. GPU/CUDA Configuration
export USE_CUDA_DOCKER=true  # Requested by user
export GLOBAL_LOG_LEVEL=INFO

# 4. Optional: Privacy & Analytics
export SCARF_NO_ANALYTICS=true
export DO_NOT_TRACK=true
export ANONYMIZED_TELEMETRY=false

echo "Starting Open WebUI with the following config:"
echo "DATABASE_URL: postgresql://${POSTGRES_USER}:****@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "USE_CUDA_DOCKER: $USE_CUDA_DOCKER"
echo "Listening on: 0.0.0.0:30072"

# Start Open WebUI
open-webui serve --host 0.0.0.0 --port 30072
