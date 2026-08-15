# Troubleshooting

This guide walks through the most common problems developers hit on Meridian and how to fix them, grouped by area. For the precise meaning of an error code, see [errors.md](./errors.md). When contacting support, always include the **`request_id`** from the error response (see [support-plans.md](./support-plans.md)).

---

## How to diagnose anything `[ts-01]`

Before diving into specifics, these four steps resolve most issues:

1. **Read the error `code` and `message`.** Meridian errors are specific; the `code` tells you exactly what's wrong. See [errors.md](./errors.md).
2. **Grab the `request_id`.** Every API error includes one (`req_…`). It lets support find your exact request.
3. **Check the status page.** `https://status.meridian.io` shows ongoing incidents. If it's us, you'll see it there.
4. **Check the audit log and build/deploy logs.** Most "it stopped working" issues have a matching entry (a key was rotated, an env var changed, a deploy failed).

---

## Authentication problems `[ts-02]`

**`401 missing_authorization`** — you didn't send the `Authorization` header, or it's malformed.
- Send `Authorization: Bearer msk_live_…`. Not a query param, not basic auth. See [authentication.md](./authentication.md#authenticating-api-requests-auth-05).

**`401 invalid_api_key`** — the key is wrong, revoked, or from the wrong mode.
- Confirm you're not mixing a `test` key against `live` data (or vice versa).
- Check the key wasn't rotated/revoked (**Settings → API Keys**, or the audit log). Meridian auto-revokes keys leaked to public GitHub — check your email. See [api-keys.md](./api-keys.md).

**`403 insufficient_scope`** — the key is valid but lacks the scope for this operation.
- Add the needed scope (e.g. `deployments:write`) or use a key that has it. See [api-keys.md](./api-keys.md#scopes-and-least-privilege-key-04).

**`403 ip_not_allowed`** — the request came from an IP not on the key's allowlist.
- Update the allowlist or call from an allowed address.

**Can't sign in to the dashboard** — reset your password (link valid 60 min), and if MFA is the blocker, use a recovery code. Lost both device and codes → `support@meridian.io` (identity verification takes up to 3 business days). See [authentication.md](./authentication.md#multi-factor-authentication-mfa-auth-03).

---

## Deployment failures `[ts-03]`

**Build fails.**
- Open the **build logs** (dashboard or `meridian logs --build`). The failing command and its output are there.
- Common causes: missing dependency, wrong Node/Python version, a build command that works locally but relies on uncommitted files. Set the correct runtime version and build command under **Settings → Build**.
- Reproduce locally with the same command Meridian runs.

**Build succeeds but the deploy is stuck in `deploying` then goes `failed`.**
- This is almost always the **health check**. Meridian waits up to 90 seconds for a passing check before failing the deploy — and keeps the old version live.
- Make sure your app **binds to the `PORT` env var** and to `0.0.0.0`, not a hardcoded port or `localhost`.
- If you set an HTTP health-check path, ensure it returns `2xx` only when truly ready. See [deployments.md](./deployments.md#health-checks-dep-06).

**Deploy succeeded but the app 502s.**
- The process may be crashing on start (check runtime logs with `meridian logs`), or listening on the wrong port.
- Verify required environment variables are set for the environment you deployed to (env vars are per-environment). See [deployments.md](./deployments.md#environments-dep-08).

**A bad version is live.**
- **Roll back** to the previous deployment (instant). Remember a rollback restores the *image* only, not env vars or database migrations. See [deployments.md](./deployments.md#rollbacks-dep-09).

**`429 deploy_rate_limited`** — too many deploys in a short window. Wait for the window to reset (respect `Retry-After`) or reduce deploy frequency. See [rate-limits.md](./rate-limits.md#default-limits-by-plan-rate-02).

---

## Rate-limit problems `[ts-04]`

**Getting `429 rate_limited`.**
- Respect the `Retry-After` header; back off exponentially with jitter. See [rate-limits.md](./rate-limits.md#handling-a-429-rate-04).
- Replace polling loops with [webhooks](./webhooks.md) — polling `GET` endpoints in a tight loop is the #1 cause of self-inflicted rate limiting.
- Use separate keys per workload so a batch job doesn't starve live traffic.

**`429 too_many_concurrent_requests`** — you have too many in-flight requests at once. Add a concurrency limit / queue on your side.

---

## Webhook problems `[ts-05]`

**Not receiving events.**
- Confirm the endpoint URL is **public HTTPS** and the event types are subscribed.
- Check **Settings → Webhooks → Recent deliveries** for attempts and response codes.
- In local dev, use a tunnel (ngrok/cloudflared) — `localhost` isn't reachable by Meridian.

**Signature verification fails.**
- Verify against the **raw** request body, not a re-serialized JSON object — byte differences break the HMAC.
- Use the correct endpoint's signing secret (each endpoint has its own).
- Allow for the 5-minute timestamp tolerance; reject anything older to prevent replay. See [webhooks.md](./webhooks.md#verifying-signatures-hook-05).

**Endpoint got auto-disabled.**
- Continuous failures for 3 days disable an endpoint. Fix it and re-enable under **Settings → Webhooks**. Meridian retries each event for up to 24 hours, so recent events can be **replayed**.

**Processing the same event twice.**
- Deliveries are at-least-once. Deduplicate on the event `id`. See [webhooks.md](./webhooks.md#idempotency-hook-06).

---

## Idempotency and duplicate actions `[ts-06]`

**A retry created two of something (two deploys, two resources).**
- Send an `Idempotency-Key` on every `POST`. Meridian returns the original result for a repeated key within 24 hours instead of acting twice. See [webhooks.md](./webhooks.md#idempotency-hook-06).

**`409 idempotency_conflict`** — you reused an idempotency key with a *different* request body. Use a fresh key for a genuinely new request, or send the identical body to fetch the original result.

---

## Billing problems `[ts-07]`

**Service got suspended.**
- Most likely an unpaid invoice after the 7-day dunning window. Update your card under **Settings → Billing**; suspended services resume automatically once paid. See [billing.md](./billing.md#failed-payments-and-dunning-bill-06).

**Unexpected charge / higher bill.**
- Check **Settings → Billing → Usage** for the metered resources driving it (compute instance-seconds, bandwidth egress, build minutes). Set **spend alerts** to catch this earlier. See [billing.md](./billing.md#how-usage-is-metered-bill-02).

**Payment keeps failing.**
- Verify the card isn't expired and allows international/online charges; add a backup card. Contact `billing@meridian.io` if it persists.

---

## Getting `5xx` from the API `[ts-08]`

- **`500 api_error`** — an unexpected error on our side. It's safe to retry idempotent requests with backoff. If it persists, capture the `request_id` and contact support.
- **`503 service_unavailable`** — temporary; back off and retry, and check `https://status.meridian.io` for an incident.
- These are **not** your fault or your code — don't loop aggressively; back off and, if widespread, wait for the incident to clear.

---

## When to contact support `[ts-09]`

Contact support when you've checked the status page, read the error `code`, and still can't resolve it — or for anything involving suspected compromise, billing disputes, or a possible platform bug. Always include:

- The **`request_id`** (from the error body or response headers).
- The **service ID** (`svc_…`) or **deployment ID** (`dep_…`) involved.
- What you expected vs. what happened, and the timestamp (UTC).

Security issues → `security@meridian.io`. Everything else → `support@meridian.io` or the in-dashboard widget. Response times depend on your plan — see [support-plans.md](./support-plans.md).

---

## Related documents

- [errors.md](./errors.md) — every error code explained.
- [deployments.md](./deployments.md) — build/health-check details.
- [rate-limits.md](./rate-limits.md) — `429` handling.
- [webhooks.md](./webhooks.md) — delivery, signatures, idempotency.
