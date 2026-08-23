#!/bin/bash
# Driver script carrying the 2-LLM FIVE_* endpoint dialect (two distinct
# endpoints: FIVE_BASE_URL and FIVE_LARGE_URL point at different hosts).
set -uo pipefail
export FIVE_MODEL="${FIVE_MODEL:-local-model}"
export FIVE_LARGE_MODEL="${FIVE_LARGE_MODEL:-local-model}"
export FIVE_BASE_URL="${FIVE_BASE_URL:-http://192.168.1.157:8080/v1}"
export FIVE_LARGE_URL="${FIVE_LARGE_URL:-http://192.168.1.161:8081/v1}"
echo "driver started"
