# Incident report: controlled HTTP failure

- Start: `{{STARTED_AT}}`
- End: `{{ENDED_AT}}`
- Injected duration: `{{DURATION_SECONDS}} seconds`
- Severity: exercise
- Status: resolved

## Summary and impact

A deterministic 100% error rate was injected into the demo API. Fill in the number of failed requests and the observed availability/error-budget impact from Grafana.

## Timeline

- `{{STARTED_AT}}` — fault injected and traffic generation started.
- `[fill in]` — black-box probe first observed failure.
- `[fill in]` — critical alert fired and webhook was received.
- `{{ENDED_AT}}` — fault removed.
- `[fill in]` — probe and burn rate returned to healthy levels.

## Detection and response

- MTTD: `[calculate from artifacts/alert-events.jsonl]`
- MTTR: `[calculate from timestamps above]`
- Runbook used: `runbooks/high-error-budget-burn.md`

## Root cause

Intentional fault injection configured the application to return HTTP 503 for all requests.

## What went well

- `[fill in from observation]`

## What could improve

- `[fill in from observation]`

## Corrective actions

| Action | Owner | Priority | Status |
|---|---|---:|---|
| Replace this exercise item with an observed improvement | Service owner | P2 | Open |

