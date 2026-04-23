#!/usr/bin/env bash
set -euo pipefail

JMETER_IMAGE=${JMETER_IMAGE:-justb4/jmeter:5.6.3}
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}

mkdir -p "${PROJECT_ROOT}/track/jmeter/results" "${PROJECT_ROOT}/track/jmeter/logs"

docker run --rm \
  -v "${PROJECT_ROOT}/track/jmeter:/tests" \
  "${JMETER_IMAGE}" \
  -n \
  -t /tests/chat_load_test.jmx \
  -l /tests/results/chat_load_test.jtl \
  -j /tests/logs/jmeter.log
