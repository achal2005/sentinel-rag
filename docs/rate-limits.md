# Rate Limits

To keep the platform fast and fair, Meridian limits how many API requests an account can make in a given window. This document explains the limits per plan, the headers we return, and how to handle a `429` correctly.

---

## How rate limiting works `[rate-01]`

Rate limits are enforced per **API key**, using a **sliding-window** counter. Each key has a per-minute request budget; when the budget is exhausted, further requests receive `429 Too Many Requests` until the window refills.

- **Live** and **test** keys have **separate** budgets, so testing never eats into production capacity.
- Limits are counted at the key level, not the whole organization, so one noisy key doesn't starve the others (subject to the account-wide ceiling on Enterprise).
- Read (`GET`) and write (`POST`/`PATCH`/`DELETE`) requests draw from the same budget unless noted below.

---

## Default limits by plan `[rate-02]`

| Plan | Requests / minute (per key) | Concurrent requests | Deploy triggers / minute |
|---|---|---|---|
| Hobby | 100 | 10 | 5 |
| Pro | 600 | 30 | 20 |
| Team | 1,200 | 60 | 40 |
| Enterprise | Custom | Custom | Custom |

- The **per-minute** column is the primary limit most integrations hit.
- **Concurrent requests** caps how many requests one key can have in flight at once; exceeding it returns `429` with code `too_many_concurrent_requests`.
- **Deploy triggers** are limited separately because builds are expensive; exceeding this returns `429` with code `deploy_rate_limited`.

Plans and their entitlements are described in [billing.md](./billing.md).

---

## Rate-limit headers `[rate-03]`

Every API response includes headers describing your current budget:

```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 594
X-RateLimit-Reset: 1754050260
```

- `X-RateLimit-Limit` — your budget for the current window.
- `X-RateLimit-Remaining` — requests left before you're limited.
- `X-RateLimit-Reset` — Unix timestamp when the window refills.

When you are limited, the `429` response also includes:

```
Retry-After: 12
```

`Retry-After` is the number of **seconds** to wait before retrying. Always prefer it over guessing.

---

## Handling a 429 `[rate-04]`

A `429` is normal and expected under load — handle it, don't panic. The response body:

```json
{
  "error": {
    "type": "rate_limit_error",
    "code": "rate_limited",
    "message": "You have exceeded the rate limit. Retry after 12 seconds.",
    "request_id": "req_7Yb31Qa"
  }
}
```

Recommended client behavior:

1. **Respect `Retry-After`.** Sleep for exactly that many seconds before retrying.
2. **Back off exponentially with jitter** if you get repeated `429`s (e.g. base delay × 2^attempt, plus a random fraction) to avoid a thundering herd.
3. **Cap retries** (e.g. 5 attempts) and surface the failure rather than looping forever.
4. **Watch `X-RateLimit-Remaining`** proactively and slow down *before* you hit zero.

Example (pseudo-code):

```text
for attempt in 0..MAX:
    resp = send(request)
    if resp.status != 429: return resp
    wait = resp.header("Retry-After") or (2 ** attempt + random())
    sleep(wait)
raise RateLimitExceeded
```

The official SDKs implement this retry logic for you by default — see [sdks-and-cli.md](./sdks-and-cli.md).

---

## Reducing how often you're limited `[rate-05]`

- **Batch and cache.** Don't poll `GET /services` in a tight loop; cache results and use [webhooks.md](./webhooks.md) to learn about changes instead of polling.
- **Use webhooks over polling** for deployments and billing events — it's both faster and cheaper on your budget.
- **Spread work over time** rather than firing thousands of requests at once.
- **Use separate keys** for separate workloads so one batch job doesn't exhaust the budget your live traffic needs.
- **Request an increase** if your legitimate traffic genuinely exceeds the plan limit.

---

## Requesting a higher limit `[rate-06]`

Pro and Team customers can request a temporary or permanent increase from **Settings → API → Rate limits → Request increase**, describing the workload and expected peak. Enterprise customers have custom limits set during onboarding and can adjust them through their account team. Include your typical and peak requests-per-minute and the key(s) involved so we can size the change.

---

## What counts against limits `[rate-07]`

- **Counted:** all authenticated REST API requests, including `GET`s.
- **Counted separately:** deploy triggers (their own budget) and concurrent in-flight requests (their own ceiling).
- **Not counted:** dashboard page loads, inbound webhook *deliveries* to your own endpoints, and requests that fail authentication with `401` before reaching the rate limiter (though repeated `401`s may trigger abuse protection).
- **Health checks** Meridian runs against *your* service are part of the platform and never count against your API budget.

---

## Frequently asked questions `[rate-08]`

**Do `GET` requests count against my limit?**
Yes. All authenticated REST requests count, including reads. Deploy triggers and concurrent requests have their own separate ceilings. See [What counts against limits](#what-counts-against-limits-rate-07).

**What's the fastest way to stop hitting limits?**
Replace polling loops with [webhooks](./webhooks.md), cache results, and use separate keys per workload so a batch job doesn't starve live traffic. See [Reducing how often you're limited](#reducing-how-often-youre-limited-rate-05).

**Do test and live keys share a budget?**
No — they're counted separately, so testing never eats into production capacity. See [How rate limiting works](#how-rate-limiting-works-rate-01).

**I legitimately need a higher limit. How do I ask?**
Request an increase under **Settings → API → Rate limits**, including your typical and peak requests-per-minute. See [Requesting a higher limit](#requesting-a-higher-limit-rate-06).

**What exactly should I do when I get a `429`?**
Sleep for the `Retry-After` seconds, then retry with exponential backoff and jitter, capping total attempts. The official SDKs do this for you. See [Handling a 429](#handling-a-429-rate-04).

---

## Related documents

- [errors.md](./errors.md) — `rate_limited`, `too_many_concurrent_requests`, `deploy_rate_limited`.
- [webhooks.md](./webhooks.md) — replace polling with events.
- [billing.md](./billing.md) — which plan you're on.
- [sdks-and-cli.md](./sdks-and-cli.md) — automatic retry/backoff.
