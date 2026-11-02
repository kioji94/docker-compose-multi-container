#!/usr/bin/env bash
# End-to-end smoke test for the compose stack.
# Usage: ./scripts/smoke-test.sh [base_url]
set -euo pipefail

BASE_URL="${1:-http://localhost:${WEB_PORT:-5000}}"
RETRIES=30

echo "==> Waiting for ${BASE_URL}/health"
for i in $(seq 1 "$RETRIES"); do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "    healthy after ${i} attempt(s)"
    break
  fi
  if [ "$i" -eq "$RETRIES" ]; then
    echo "FAIL: service did not become healthy" >&2
    exit 1
  fi
  sleep 2
done

echo "==> Health reports database reachable"
curl -fsS "${BASE_URL}/health" | grep -q '"database":"reachable"' \
  || curl -fsS "${BASE_URL}/health" | grep -q '"database": "reachable"'

MARKER="smoke-test-$(date +%s)"

echo "==> POST /notes (write through web -> db)"
curl -fsS -X POST "${BASE_URL}/notes" \
  -H 'Content-Type: application/json' \
  -d "{\"content\": \"${MARKER}\"}" >/dev/null

echo "==> GET /notes (read back from db)"
curl -fsS "${BASE_URL}/notes" | grep -q "${MARKER}"

echo "==> POST /notes with empty body returns 400"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}/notes" \
  -H 'Content-Type: application/json' -d '{}')
[ "$code" = "400" ]

echo "PASS: all smoke tests succeeded"
