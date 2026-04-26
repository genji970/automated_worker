#!/usr/bin/env bash
set -euo pipefail

BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://host.docker.internal:9000/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:-local-dev-key}"
OPEN_WEBUI_PORT="${OPEN_WEBUI_PORT:-8080}"

docker rm -f open-webui || true

docker run -d \
  --name open-webui \
  --restart always \
  -p "${OPEN_WEBUI_PORT}:8080" \
  -e OPENAI_API_BASE_URL="${BACKEND_BASE_URL}" \
  -e OPENAI_API_BASE_URLS="${BACKEND_BASE_URL}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e OPENAI_API_KEYS="${OPENAI_API_KEY}" \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main

echo "Open WebUI: http://localhost:${OPEN_WEBUI_PORT}"
echo "Open WebUI backend base URL: ${BACKEND_BASE_URL}"
