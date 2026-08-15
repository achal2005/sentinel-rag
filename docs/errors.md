# Errors

This is the canonical reference for Meridian API errors: the response format, HTTP status codes, and every error `code` you might see. For step-by-step fixes, see [troubleshooting.md](./troubleshooting.md).

---

## Error response format `[err-01]`

Every API error returns a JSON body with a single `error` object:

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "parameter_missing",
    "message": "Missing required parameter: name.",
    "param": "name",
    "request_id": "req_7Yb31Qa",
    "doc_url": "https://docs.meridian.io/errors#parameter_missing"
  }
}
```

| Field | Meaning |
|---|---|
| `type` | High-level category (see below). Use for coarse handling. |
| `code` | The specific, stable machine-readable error. **Switch on this.** |
| `message` | Human-readable explanation. May change wording — never parse it. |
| `param` | The offending parameter, when applicable. |
| `request_id` | Unique ID for this request. **Always include it in support tickets.** |
| `doc_url` | Link to the relevant docs section. |

> **Rule:** branch your code on `code`, never on `message`. Message text can change without a version bump, per [api-versions.md](./api-versions.md#what-counts-as-a-breaking-change-ver-04).

---

## HTTP status codes `[err-02]`

| Status | Meaning | Retry? |
|---|---|---|
| `200` / `201` | Success | — |
| `204` | Success, no content (e.g. delete) | — |
| `400` | Bad request — malformed or invalid input | No (fix the request) |
| `401` | Not authenticated | No (fix credentials) |
| `403` | Authenticated but not permitted | No (fix scope/role/IP) |
| `404` | Resource not found | No |
| `409` | Conflict (idempotency or state) | No (usually) |
| `422` | Validation failed | No (fix the data) |
| `429` | Rate limited | **Yes**, after `Retry-After` |
| `500` | Unexpected server error | Yes, with backoff |
| `503` | Temporarily unavailable | Yes, with backoff |

---

## Error types `[err-03]`

| `type` | Typical status | Meaning |
|---|---|---|
| `invalid_request_error` | 400 / 404 / 422 | Something about the request is wrong |
| `authentication_error` | 401 | Missing or invalid credentials |
| `permission_error` | 403 | Valid credentials, insufficient permission |
| `rate_limit_error` | 429 | You exceeded a rate limit |
| `idempotency_error` | 409 | Idempotency key reused with a different body |
| `conflict_error` | 409 | Resource state conflict |
| `api_error` | 500 | Unexpected error on Meridian's side |
| `service_unavailable_error` | 503 | Temporary outage or maintenance |

---

## Authentication errors (401) `[err-04]`

| `code` | Meaning | Fix |
|---|---|---|
| `missing_authorization` | No `Authorization` header | Send `Authorization: Bearer <key>` |
| `invalid_api_key` | Key is wrong, revoked, or expired | Check the key; ensure live/test mode matches |
| `invalid_token` | PAT/OAuth token invalid or expired | Re-authenticate; refresh the token |
| `mode_mismatch` | Test key used against live resources (or vice versa) | Use the correct key for the mode |

See [authentication.md](./authentication.md) and [api-keys.md](./api-keys.md).

---

## Permission errors (403) `[err-05]`

| `code` | Meaning | Fix |
|---|---|---|
| `insufficient_scope` | Key lacks the required scope | Add the scope or use a broader key |
| `insufficient_role` | User's role can't perform this action | Ask an Admin/Owner, or get a higher role |
| `ip_not_allowed` | Source IP not on the key's allowlist | Call from an allowed IP or update the allowlist |
| `mfa_required` | Org requires MFA and you haven't enrolled | Enroll a second factor |

See [account-management.md](./account-management.md#roles-and-permissions-acct-02).

---

## Request/validation errors (400 / 404 / 422) `[err-06]`

| `code` | Status | Meaning |
|---|---|---|
| `parameter_missing` | 400 | A required parameter is absent (`param` names it) |
| `parameter_invalid` | 400 | A parameter has the wrong type or format |
| `parameter_unknown` | 400 | An unrecognized parameter was sent |
| `validation_failed` | 422 | The input is well-formed but fails business rules |
| `resource_not_found` | 404 | No resource with that ID exists |
| `resource_already_exists` | 409 | A uniquely named resource already exists |
| `unsupported_version` | 400 | The `Meridian-Version` header value isn't recognized |

---

## Conflict & idempotency errors (409) `[err-07]`

| `code` | Meaning | Fix |
|---|---|---|
| `idempotency_conflict` | Idempotency key reused with a different request body | Use a new key, or resend the identical body |
| `resource_conflict` | The resource is in a state that blocks this action (e.g. deleting a service mid-deploy) | Wait for the current operation, then retry |
| `deployment_in_progress` | A deploy is already running for this environment | Wait for it to finish or cancel it |

See [webhooks.md](./webhooks.md#idempotency-hook-06).

---

## Rate-limit errors (429) `[err-08]`

| `code` | Meaning | Fix |
|---|---|---|
| `rate_limited` | Per-minute request budget exceeded | Wait `Retry-After` seconds; back off |
| `too_many_concurrent_requests` | Too many in-flight requests on the key | Add client-side concurrency limits |
| `deploy_rate_limited` | Too many deploy triggers in the window | Reduce deploy frequency |

See [rate-limits.md](./rate-limits.md#handling-a-429-rate-04).

---

## Server errors (500 / 503) `[err-09]`

| `code` | Status | Meaning | Fix |
|---|---|---|---|
| `api_error` | 500 | Unexpected internal error | Retry idempotent requests with backoff; capture `request_id` |
| `service_unavailable` | 503 | Temporary outage/maintenance | Back off; check `https://status.meridian.io` |
| `timeout` | 503 | The operation took too long upstream | Retry with backoff |

These indicate a problem on Meridian's side. If a `500` persists, send the `request_id` to `support@meridian.io`.

---

## Handling errors well `[err-10]`

- **Switch on `code`**, fall back on `type`, show `message` to humans, log `request_id`.
- **Retry only** `429`, `500`, and `503` — with `Retry-After` where present and exponential backoff + jitter otherwise. Never retry `400`/`401`/`403`/`404`/`422` unchanged; fix the request.
- **Make writes idempotent** with `Idempotency-Key` so retries are safe.
- **Log `request_id` on every failure** — it's the single fastest way for support to help you.

---

## Frequently asked questions `[err-11]`

**Should I branch my code on the error `message`?**
No. Switch on `code` (stable, machine-readable). The `message` wording can change without a version bump. See [Error response format](#error-response-format-err-01).

**Which errors are safe to retry?**
Only `429`, `500`, and `503` — with `Retry-After` where present and exponential backoff otherwise. Never retry `400`/`401`/`403`/`404`/`422` unchanged; fix the request first. See [Handling errors well](#handling-errors-well-err-10).

**Where do I find the `request_id`?**
In the `error` object of every failed response (and in response headers). Include it in every support ticket — it's the fastest way for us to locate your request. See [Error response format](#error-response-format-err-01).

**What's the difference between `insufficient_scope` and `insufficient_role`?**
`insufficient_scope` means an **API key** lacks the needed scope; `insufficient_role` means a **user's role** can't perform the action. See [Permission errors](#permission-errors-err-05).

**I got a `409 idempotency_conflict`. What happened?**
You reused an `Idempotency-Key` with a **different** request body. Use a fresh key for a new request, or resend the identical body to get the original result. See [Conflict & idempotency errors](#conflict--idempotency-errors-409-err-07).

---

## Related documents

- [troubleshooting.md](./troubleshooting.md) — symptom-to-fix walkthroughs.
- [rate-limits.md](./rate-limits.md) — `429` behavior.
- [authentication.md](./authentication.md) / [api-keys.md](./api-keys.md) — `401`/`403` causes.
- [api-versions.md](./api-versions.md) — why to switch on `code`, not `message`.
