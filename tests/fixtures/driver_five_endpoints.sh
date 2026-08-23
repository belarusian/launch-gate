#!/bin/bash
# Driver script carrying the FIVE_* endpoint exports (seed dialect).
set -uo pipefail
export FIVE_MODEL="${FIVE_MODEL:-local-model}"
export FIVE_LARGE_MODEL="${FIVE_LARGE_MODEL:-local-model}"
export FIVE_BASE_URL="${FIVE_BASE_URL:-http://192.168.1.161:8080/v1}"
export FIVE_LARGE_URL="${FIVE_LARGE_URL:-http://192.168.1.161:8080/v1}"
echo "driver started"
