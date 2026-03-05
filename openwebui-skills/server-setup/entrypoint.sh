#!/usr/bin/env bash
# =============================================================================
# entrypoint.sh — Start MinerU API server in background, then launch OpenWebUI
# =============================================================================
set -e

# --- MinerU Content Extraction API (pipeline mode, no vLLM) ---
if command -v mineru-api &>/dev/null; then
  echo "[entrypoint] Starting MinerU API on 127.0.0.1:8000 ..."
  mineru-api --host 127.0.0.1 --port 8000 &
  MINERU_PID=$!
  echo "[entrypoint] MinerU API started (PID=${MINERU_PID})"
else
  echo "[entrypoint] WARN: mineru-api not found — skipping content extraction server"
fi

# --- Launch OpenWebUI (original start.sh from base image) ---
exec bash start.sh
