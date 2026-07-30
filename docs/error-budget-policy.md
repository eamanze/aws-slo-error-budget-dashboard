# Error-budget policy

The 99.5% availability objective permits a 0.5% failure budget over 28 rolling days.

| Remaining budget | Delivery policy |
|---:|---|
| More than 50% | Normal releases with standard controls |
| 25–50% | Review high-risk changes and increase monitoring |
| 0–25% | Reliability work takes priority; exceptions require service-owner approval |
| Exhausted | Freeze non-remediation changes until the short-window burn is healthy and corrective work is agreed |

Planned maintenance counts against the SLO when it affects the measured user journey. Monitoring gaps are documented and do not silently count as success.

