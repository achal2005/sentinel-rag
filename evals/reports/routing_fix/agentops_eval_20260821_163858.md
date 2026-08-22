# AgentOps Evaluation

Generated: 2026-08-21T11:08:58.705518+00:00

| Result | Count |
|---|---:|
| Total cases | 25 |
| Executed | 9 |
| Passed | 0 |
| Failed | 9 |
| Errors | 0 |
| Not implemented / domain binding | 16 |
| Overall pass rate (executed only) | 0.0% |
| Critical policy | PASS |
| Critical checks unverified | 0 |

## Capability metrics

Denominators include only checks that actually ran; `NOT_IMPLEMENTED` is never counted as a pass.

| Capability | Passed | Failed/error | Not implemented | Rate |
|---|---:|---:|---:|---:|
| routing | 16 | 9 | 0 | 64.0% |

## Categories

| Category | Total | Passed | Failed | Errors | Not implemented |
|---|---:|---:|---:|---:|---:|
| intent_routing | 25 | 0 | 9 | 0 | 16 |

## Critical failures

None.

## Critical checks not yet verifiable

None.

## Failed and errored cases

| Case | Category | Failed checks |
|---|---|---|
| ROUTE-003 | intent_routing | route: expected 'escalate', got 'action' |
| ROUTE-004 | intent_routing | route: expected 'answer', got 'escalate' |
| ROUTE-005 | intent_routing | route: expected 'answer', got 'escalate' |
| ROUTE-006 | intent_routing | route: expected 'escalate', got 'action' |
| ROUTE-008 | intent_routing | route: expected 'action', got 'escalate' |
| ROUTE-013 | intent_routing | route: expected 'action', got 'escalate' |
| ROUTE-015 | intent_routing | route: expected 'spam', got 'escalate' |
| ROUTE-017 | intent_routing | route: expected 'action', got 'escalate' |
| ROUTE-019 | intent_routing | route: expected 'action', got 'escalate' |
