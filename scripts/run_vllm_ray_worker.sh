#!/usr/bin/env bash
set -euo pipefail

HEAD_IP=${HEAD_IP:?HEAD_IP is required}
RAY_PORT=${RAY_PORT:-6379}

export PYTHONUNBUFFERED=1

ray stop || true
ray start --address="${HEAD_IP}:${RAY_PORT}" --block
