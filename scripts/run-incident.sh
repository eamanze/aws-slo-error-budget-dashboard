#!/usr/bin/env bash
set -euo pipefail

duration="${INCIDENT_DURATION_SECONDS:-180}"
started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cleanup() {
  ./scripts/fault.sh clear >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "Starting controlled error incident at $started for ${duration}s"
./scripts/fault.sh errors >/dev/null

end=$((SECONDS + duration))
while (( SECONDS < end )); do
  python3 load-tests/load.py --requests 20 --concurrency 5 || true
  sleep 5
done

./scripts/fault.sh clear >/dev/null
ended="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
trap - EXIT INT TERM

mkdir -p artifacts
docker compose cp incident-receiver:/artifacts/alert-events.jsonl artifacts/alert-events.jsonl >/dev/null 2>&1 || true
report="artifacts/incident-${started//[:]/-}.md"
sed \
  -e "s/{{STARTED_AT}}/$started/g" \
  -e "s/{{ENDED_AT}}/$ended/g" \
  -e "s/{{DURATION_SECONDS}}/$duration/g" \
  docs/incident-template.md > "$report"
echo "Fault cleared. Draft incident report: $report"
