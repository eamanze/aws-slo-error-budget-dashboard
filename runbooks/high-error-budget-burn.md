# Runbook: high availability error-budget burn

## Trigger

`AvailabilitySLOBurnRateCritical` or `AvailabilitySLOBurnRateWarning` indicates that independent HTTP probes are consuming the 99.5% availability error budget too quickly.

## Immediate actions

1. Acknowledge the alert and record the incident start time.
2. Confirm user impact in Grafana’s **User-visible reliability** panel and inspect `probe_http_status_code`.
3. Check application health with `curl -i http://localhost:8080/readyz` and `docker compose ps`.
4. Inspect recent changes and logs with `docker compose logs --since=15m app`.
5. Mitigate before diagnosing deeply: clear an injected fault, roll back the latest release, or restore the last healthy task definition.
6. Confirm recovery through both the black-box probe and request-success SLI.

## Escalation

- Page the service owner immediately for the critical alert.
- Engage the platform owner if the application is healthy but the ALB, network path, or probe remains unhealthy.
- Open a status update if impact lasts longer than 15 minutes.

## Validation and closure

- The probe has succeeded continuously for at least 10 minutes.
- The short-window burn rate is below 1x.
- A follow-up incident report records impact, detection, mitigation, and corrective actions.

