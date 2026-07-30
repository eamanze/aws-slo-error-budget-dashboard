#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
token="${FAULT_TOKEN:-local-development-only}"
url="${APP_URL:-http://localhost:8080}"

case "$action" in
  errors)
    curl --fail --silent --show-error -X POST "$url/admin/fault" \
      -H "X-Fault-Token: $token" -H 'Content-Type: application/json' \
      --data '{"error_rate":1}'
    ;;
  latency)
    curl --fail --silent --show-error -X POST "$url/admin/fault" \
      -H "X-Fault-Token: $token" -H 'Content-Type: application/json' \
      --data '{"latency_ms":750}'
    ;;
  unhealthy)
    curl --fail --silent --show-error -X POST "$url/admin/fault" \
      -H "X-Fault-Token: $token" -H 'Content-Type: application/json' \
      --data '{"unhealthy":true}'
    ;;
  clear)
    curl --fail --silent --show-error -X DELETE "$url/admin/fault" \
      -H "X-Fault-Token: $token"
    ;;
  *)
    echo "usage: $0 {errors|latency|unhealthy|clear}" >&2
    exit 2
    ;;
esac
echo

