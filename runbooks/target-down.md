# Runbook: application metrics target down

This alert means telemetry is missing; it does not by itself prove user impact. Check the independent black-box probe first.

1. Open Prometheus `/targets` and capture the scrape error.
2. Check `docker compose ps app` and `docker compose logs --since=15m app`.
3. Query the endpoint directly: `curl -fsS http://localhost:8080/metrics`.
4. If users are affected, follow [high-error-budget-burn.md](high-error-budget-burn.md).
5. If only telemetry is affected, restore scrape connectivity or metric exposition and annotate the monitoring gap.

