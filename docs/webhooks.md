# Webhooks

Webhooks let Meridian notify your systems when something happens in your account — a deployment finishes, a service is suspended, an invoice is paid. Instead of polling the API, you register an endpoint and Meridian POSTs a signed event to it.

---

## How webhooks work `[hook-01]`

1. You register an **endpoint** (a public HTTPS URL) and subscribe it to one or more event types.
2. When a subscribed event occurs, Meridian sends an HTTP `POST` to your URL with a JSON body.
3. Your endpoint verifies the signature, does its work, and responds with `2xx`.
4. If your endpoint fails or is slow, Meridian **retries** with backoff.

Webhooks are the recommended way to react to asynchronous events like deployments and billing.

---

## Registering an endpoint `[hook-02]`

**Dashboard:** **Settings → Webhooks → Add endpoint**. Enter your HTTPS URL, select event types, and copy the **signing secret** (`whsec_…`) shown once.

**API:**
```bash
curl https://api.meridian.io/v1/webhook_endpoints \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/hooks/meridian",
    "events": ["deployment.succeeded", "deployment.failed", "invoice.paid"]
  }'
```

The response includes the endpoint `id` and its `secret`. Store the secret securely — you need it to verify signatures.

An endpoint must be a **public HTTPS URL**. During local development, use a tunnel (ngrok, cloudflared) to expose your machine, or use test-mode events fired from the dashboard.

---

## Event object `[hook-03]`

Every delivery has the same envelope:

```json
{
  "id": "evt_5Hn28aQ",
  "object": "event",
  "type": "deployment.succeeded",
  "api_version": "2025-08-01",
  "created_at": "2025-08-01T12:30:00Z",
  "data": {
    "object": {
      "id": "dep_9Kd02mQ",
      "object": "deployment",
      "service_id": "svc_8Kd02mQ",
      "environment": "production",
      "status": "live",
      "url": "https://sunny-meadow-1234.meridian.app"
    }
  }
}
```

- `id` — unique event ID; use it for [idempotency](#idempotency-hook-06).
- `type` — the event type (see the catalog below).
- `api_version` — the API version whose object shape the `data` follows. Pin your parsing to it; new fields may appear per [api-versions.md](./api-versions.md#what-counts-as-a-breaking-change-ver-04).
- `data.object` — the resource that triggered the event.

---

## Event catalog `[hook-04]`

| Event type | Fires when |
|---|---|
| `deployment.created` | A deployment is queued |
| `deployment.succeeded` | A deployment becomes `live` |
| `deployment.failed` | A build or health check fails |
| `deployment.rolled_back` | A deployment is superseded by a rollback |
| `service.created` | A new service is created |
| `service.suspended` | A service is suspended (e.g. unpaid invoice) |
| `service.resumed` | A suspended service is restored |
| `invoice.created` | A new invoice is generated |
| `invoice.paid` | An invoice is paid successfully |
| `invoice.payment_failed` | A charge attempt fails |
| `member.invited` | A member is invited to the organization |
| `member.removed` | A member is removed |
| `api_key.created` | An API key is created |
| `api_key.revoked` | An API key is revoked |

New event types are added over time. Treat unknown `type` values gracefully rather than erroring.

---

## Verifying signatures `[hook-05]`

**Always verify** that a webhook genuinely came from Meridian before acting on it. Each request includes a `Meridian-Signature` header:

```
Meridian-Signature: t=1754050200,v1=5257a869e7d0f0b5e3...
```

- `t` — the Unix timestamp when the event was signed.
- `v1` — an HMAC-SHA256 signature of the string `"{t}.{raw_request_body}"`, using your endpoint's signing secret as the key.

To verify:

1. Read the **raw** request body (do not re-serialize the parsed JSON — whitespace matters).
2. Build the signed payload: `signed = f"{t}.{raw_body}"`.
3. Compute `HMAC-SHA256(signing_secret, signed)` and hex-encode it.
4. Compare it to `v1` using a **constant-time** comparison.
5. Reject the event if the timestamp `t` is more than **5 minutes** from now (this blocks replay attacks).

Example (Python):

```python
import hmac, hashlib, time

def verify(raw_body: bytes, header: str, secret: str, tolerance: int = 300) -> bool:
    parts = dict(kv.split("=", 1) for kv in header.split(","))
    t, sig = int(parts["t"]), parts["v1"]
    if abs(time.time() - t) > tolerance:
        return False
    signed = f"{t}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
```

The official SDKs expose `meridian.webhooks.verify(...)` so you don't implement this by hand — see [sdks-and-cli.md](./sdks-and-cli.md).

---

## Idempotency `[hook-06]`

Meridian guarantees **at-least-once** delivery, so your endpoint may receive the same event more than once (for example, if your `2xx` response was lost). Make handling idempotent:

- Record processed event `id`s and ignore duplicates, **or**
- Make the downstream action naturally idempotent (upserts, not blind inserts).

The same principle applies when *you* call the API: send an `Idempotency-Key` header on `POST` requests so retries don't create duplicate resources. Meridian remembers an idempotency key's result for **24 hours** and returns the original response on replay. A reused key with a *different* request body returns `409 idempotency_conflict` (see [errors.md](./errors.md)).

---

## Retries and delivery `[hook-07]`

If your endpoint doesn't return a `2xx` within **10 seconds**, or returns a `5xx`, Meridian retries with exponential backoff:

- Retry schedule: after ~1 min, 5 min, 30 min, 2 hr, then every 6 hr.
- Meridian keeps retrying for up to **24 hours**, after which the delivery is marked **failed** and abandoned.
- Return `2xx` **as soon as** you've stored the event; do slow work asynchronously so you don't hit the 10-second timeout.
- A `4xx` (other than `429`) is treated as a permanent rejection and is **not** retried — so don't return `400` for transient problems.

You can inspect and **replay** individual deliveries under **Settings → Webhooks → {endpoint} → Recent deliveries**, or via `POST /v1/webhook_endpoints/{id}/deliveries/{delivery_id}/retry`.

---

## Disabling and rotating `[hook-08]`

- **Auto-disable:** if an endpoint fails continuously for **3 days**, Meridian disables it and emails the organization owners. Re-enable it after fixing the endpoint.
- **Rotate the secret:** **Settings → Webhooks → {endpoint} → Roll secret** issues a new signing secret with a short overlap window so you can deploy the new secret without dropping events.

---

## Best practices `[hook-09]`

- Verify **every** signature and reject stale timestamps.
- Respond fast (`2xx` immediately), process asynchronously.
- Be idempotent on event `id`.
- Subscribe only to the events you use.
- Don't trust the payload's `data` for security-critical values without re-fetching from the API if the stakes are high.
- Monitor the **Recent deliveries** view for failures.

---

## Frequently asked questions `[hook-10]`

**Why did I receive the same event twice?**
Delivery is **at-least-once**, so duplicates are expected. Deduplicate on the event `id`, or make the downstream action idempotent. See [Idempotency](#idempotency-hook-06).

**My signature verification keeps failing. What's wrong?**
The most common cause is verifying against a re-serialized JSON body instead of the **raw** request bytes. Use the raw body, the correct endpoint's signing secret, and allow the 5-minute timestamp tolerance. See [Verifying signatures](#verifying-signatures-hook-05).

**Can I point a webhook at `localhost` during development?**
No — the endpoint must be a public HTTPS URL. Use a tunnel (ngrok, cloudflared) to expose your local server, or fire test events from the dashboard. See [Registering an endpoint](#registering-an-endpoint-hook-02).

**My endpoint got disabled. Why, and how do I recover?**
Continuous failures for **3 days** auto-disable an endpoint. Fix it, re-enable it under **Settings → Webhooks**, and **replay** recent deliveries (Meridian retries each event for up to 24 hours). See [Disabling and rotating](#disabling-and-rotating-hook-08).

**How long does Meridian keep retrying a failed delivery?**
Up to **24 hours** with exponential backoff, after which the delivery is marked failed. Return `2xx` quickly and process asynchronously. See [Retries and delivery](#retries-and-delivery-hook-07).

**Should I trust the values in the payload for security-critical actions?**
For high-stakes actions, re-fetch the resource from the API rather than trusting the payload alone. See [Best practices](#best-practices-hook-09).

---

## Related documents

- [deployments.md](./deployments.md) — deployment events.
- [billing.md](./billing.md) — invoice events.
- [sdks-and-cli.md](./sdks-and-cli.md) — built-in signature verification.
- [errors.md](./errors.md) — `idempotency_conflict` and related codes.
