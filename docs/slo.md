# Service level objectives

## User journey

The measured journey is an unauthenticated client receiving a successful response from `GET /`. Administrative, metric, liveness, and readiness paths are excluded.

## Availability

- SLI: proportion of independent HTTP probes returning status 200.
- Objective: **99.5% over a rolling 28-day window**.
- Error budget: 0.5%, approximately 3 hours 21 minutes in 28 days at continuous traffic.
- Measurement: Blackbox Exporter, not in-process counters, so total application failure remains measurable.

## Latency

- SLI: proportion of `GET /` requests completing in at most 500 ms.
- Objective: **99% over a rolling 28-day window**.
- Diagnostic: p95 latency is displayed but is not itself the compliance calculation.

The local dashboard uses a five-minute latency SLI to make exercises visible quickly. A production deployment should also record and retain the 28-day compliance series.

## Multi-window burn alerts

Availability alerts combine a short and long window to limit noisy pages:

| Alert | Windows | Burn threshold | Intent |
|---|---|---:|---|
| Critical | 5m and 1h | 14.4x | Page on rapid exhaustion |
| Warning | 30m and 6h | 3x | Ticket sustained degradation |

Both sides of a window pair must breach. Critical alerts inhibit warnings for the same service.

