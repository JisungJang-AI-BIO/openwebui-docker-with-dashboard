# =============================================================================
# OpenWebUI-Skills — Custom Docker Image
# Extends an official OpenWebUI image with document processing dependencies.
#
# Build (standalone):
#   docker build -t openwebui-skills .
#
# Build (extend your existing image):
#   docker build --build-arg BASE_IMAGE=ghcr.io/open-webui/open-webui:cuda \
#     -t openwebui-skills:cuda .
#
# Run:
#   docker compose up -d
# =============================================================================

ARG BASE_IMAGE=ghcr.io/open-webui/open-webui:main
FROM ${BASE_IMAGE}

# --- Metadata ---
LABEL maintainer="JisungJang-AI-BIO"
LABEL description="OpenWebUI with Anthropic Skills dependencies (LibreOffice, Pandoc, Tesseract, Node.js, etc.)"

# --- System dependencies ---
USER root

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        libreoffice \
        pandoc \
        poppler-utils \
        qpdf \
        tesseract-ocr \
        tesseract-ocr-kor \
        nodejs \
        npm \
        fonts-nanum \
        fonts-nanum-coding \
        fonts-nanum-extra \
        git \
    && fc-cache -fv \
    && npm install -g docx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Project files ---
WORKDIR /app/OpenWebUI-Skills

COPY requirements.txt ./
COPY server-setup/ ./server-setup/
COPY tools/ ./tools/
COPY skills/ ./skills/
COPY tests/ ./tests/

# --- Python dependencies ---
RUN pip install --no-cache-dir -r requirements.txt

# --- MinerU (PDF content extraction engine, pipeline mode) ---
RUN pip install --no-cache-dir "mineru[core]" && \
    mineru-models-download || echo "WARN: MinerU model download failed (will retry at runtime)"

# --- Pre-download embedding models (switch via Admin > Documents > Embedding Model) ---
ENV SENTENCE_TRANSFORMERS_HOME=/opt/embedding-models
RUN python3 -c "\
from sentence_transformers import SentenceTransformer; \
print('Downloading Qwen3-Embedding-0.6B...'); SentenceTransformer('Qwen/Qwen3-Embedding-0.6B'); \
print('Downloading Qwen3-Embedding-4B...');  SentenceTransformer('Qwen/Qwen3-Embedding-4B'); \
print('Downloading Qwen3-Embedding-8B...');  SentenceTransformer('Qwen/Qwen3-Embedding-8B'); \
print('All embedding models downloaded.')"

# --- Anthropic vendor scripts ---
RUN bash server-setup/clone-anthropic-scripts.sh /app/OpenWebUI-Skills

# --- Entrypoint: start MinerU API + OpenWebUI ---
COPY server-setup/entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

# Restore base image's working directory so start.sh is found on container startup
WORKDIR /app/backend
CMD ["bash", "entrypoint.sh"]
