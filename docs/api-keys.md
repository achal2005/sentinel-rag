# API Keys

API keys are the credentials your applications use to call the Meridian REST API. This document covers the types of keys, how to create and scope them, how to rotate and revoke them safely, and best practices for keeping them secret.

For how keys are *sent* on a request, and for human/CLI authentication, see [authentication.md](./authentication.md).

---

## Key types `[key-01]`

Meridian issues two kinds of API keys plus webhook signing secrets.

| Type | Prefix | Where it's used | Can it be public? |
|---|---|---|---|
| Secret key | `msk_live_…` / `msk_test_…` | Server-side code, CI, backend services | **No — keep secret** |
| Publishable key | `mpk_live_…` / `mpk_test_…` | Browser/front-end, identifies the account | Yes, safe to expose |
| Webhook signing secret | `whsec_…` | Verifying inbound webhooks | **No — keep secret** |

- **`live`** keys act on real resources and real billing.
- **`test`** keys operate against an isolated sandbox: test-mode services, no charges, and separate rate-limit counters. Use them freely in development and CI. See [rate-limits.md](./rate-limits.md).

A key value is shown **once**, at creation. Meridian stores only a hash, so we cannot recover a lost key — you rotate to a new one instead.

---

## Anatomy of a key `[key-02]`

```
msk_live_9fK2aQ7wZ0pR4tN6xB8cY1sD3vH5jL7m
│   │    │
│   │    └── 32-character random secret (never logged in full)
│   └─────── mode: live or test
└─────────── type: msk (secret), mpk (publishable)
```

Only the **last 4 characters** are ever displayed after creation (for example, `…jL7m`), so you can tell keys apart in a list without exposing them.

---

## Creating a key `[key-03]`

**Dashboard:** **Settings → API Keys → Create secret key**. Give it a descriptive name (for example `billing-worker-prod`), choose its **scopes** (see below), optionally restrict it by **IP allowlist**, and copy the value immediately.

**API:** you can mint scoped keys programmatically with an existing admin key:

```bash
curl https://api.meridian.io/v1/api_keys \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ci-deploy-key",
    "scopes": ["deployments:read", "deployments:write"],
    "ip_allowlist": ["203.0.113.10/32"]
  }'
```

The response includes the full key **once**, under the `secret` field:

```json
{
  "id": "key_3Nb71Qa",
  "object": "api_key",
  "name": "ci-deploy-key",
  "scopes": ["deployments:read", "deployments:write"],
  "last4": "a8Kd",
  "secret": "msk_live_...full-value-shown-once...",
  "created_at": "2025-08-01T10:00:00Z"
}
```

Store the `secret` in your secrets manager right away; you cannot retrieve it later.

---

## Scopes and least privilege `[key-04]`

By default a secret key has **full access** to your organization. Prefer scoped keys so a leak has a limited blast radius. Scopes follow a `resource:action` pattern:

| Scope | Grants |
|---|---|
| `services:read` | List and read services |
| `services:write` | Create, update, delete services |
| `deployments:read` | View deployments and build logs |
| `deployments:write` | Trigger deploys, rollbacks, cancels |
| `env:read` / `env:write` | Read/write environment variables |
| `billing:read` | View invoices and usage |
| `members:read` / `members:write` | Manage organization members |
| `webhooks:write` | Manage webhook endpoints |
| `*` | Full access (avoid for automation) |

Give each service the narrowest set it needs. A CI pipeline that only deploys needs `deployments:write` and nothing else. A key that lacks a required scope returns `403 insufficient_scope` (see [errors.md](./errors.md#permission-errors-err-05)).

---

## Publishable keys `[key-05]`

Publishable keys (`mpk_live_…`) are meant to be embedded in front-end code. They can only perform a fixed, safe set of read-mostly operations (for example, reading public service status) and can **never** read secrets, change resources, or view billing. If you find yourself wanting a publishable key to do more, you actually need a backend endpoint that holds a secret key.

---

## Regenerating (rotating) a secret key `[key-06]`

Rotate a key on a schedule, and immediately if it may have leaked. **Rotation without downtime** works because Meridian lets a key have a short **grace period**:

1. In **Settings → API Keys**, click **⋯ → Rotate** on the key (or `POST /v1/api_keys/{id}/rotate`).
2. Meridian issues a **new** secret and keeps the **old** one valid for a grace window you choose: **immediately, 1 hour, 24 hours, or 7 days**.
3. Deploy the new secret to all services that use it.
4. When traffic on the old key drops to zero (watch **Last used** in the dashboard), the old secret expires at the end of the window — or revoke it early.

```bash
curl https://api.meridian.io/v1/api_keys/key_3Nb71Qa/rotate \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{ "grace_period": "24h" }'
```

The response returns the new `secret` and the `expires_at` of the old one.

---

## Revoking a key `[key-07]`

Revocation is **immediate and permanent**. Use it when a key is compromised or no longer needed.

- **Dashboard:** **Settings → API Keys → ⋯ → Revoke**.
- **API:** `DELETE /v1/api_keys/{id}`.

Within a few seconds, every region rejects the revoked key with `401 invalid_api_key`. There is no undo — if you revoke the wrong key, create a new one. Revoking the **last** admin key is blocked to prevent you from locking yourself out; create a replacement first.

---

## IP allowlists `[key-08]`

Any secret key can be restricted to a list of source IP addresses or CIDR ranges. Requests from other addresses are rejected with `403 ip_not_allowed` before the key is even evaluated. This is strongly recommended for keys used by fixed infrastructure (CI runners, a static NAT gateway). Update the allowlist under **Settings → API Keys → ⋯ → Edit**, or via `PATCH /v1/api_keys/{id}`.

---

## Keeping keys secret `[key-09]`

- **Never** commit keys to source control. Use environment variables or a secrets manager. Meridian scans public GitHub for leaked `msk_live_` keys and will **auto-revoke** and email you if one is found.
- **Never** log the full key. Log the `last4` if you need to correlate.
- Use **`test`-mode keys** in development and CI whenever possible.
- Give each service and environment its **own** key so you can rotate or revoke one without affecting the others.
- Set an **expiry** on keys you know are temporary.
- Review **Last used** timestamps periodically and revoke stale keys.

---

## Viewing key activity `[key-10]`

Each key's detail page shows its **Last used** time, the **source IPs** seen recently, and a link to the audit log of administrative actions (created, rotated, revoked, scope-changed). Programmatically, `GET /v1/api_keys` lists all keys with their `last4`, `scopes`, `last_used_at`, and `created_at` — never the secret itself.

---

## Frequently asked questions `[key-11]`

**I lost my secret key — can you resend it?**
No. Meridian stores only a hash of each key, so we cannot recover the value. **Rotate** to a new key instead. See [Regenerating a secret key](#regenerating-rotating-a-secret-key-key-06).

**What's the difference between a `test` and `live` key?**
`test` keys operate against an isolated sandbox — no real resources, no billing, separate rate-limit counters. Use them in development and CI. See [Key types](#key-types-key-01).

**How do I rotate a key without downtime?**
Rotate with a **grace period** (immediately, 1h, 24h, or 7d): deploy the new secret while the old one still works, then let the old one expire once its **Last used** drops to zero. See [key-06](#regenerating-rotating-a-secret-key-key-06).

**I accidentally pushed a key to a public repo. What happens?**
Meridian scans public GitHub and will **auto-revoke** a leaked `msk_live_` key and email you. Rotate any related secrets and review the audit log. See [Keeping keys secret](#keeping-keys-secret-key-09).

**How many API keys can I create?**
There's no hard limit. Best practice is **one key per service and environment**, each with least-privilege scopes, so you can rotate or revoke one without affecting the others.

**Can a publishable key read my resources?**
No. Publishable keys (`mpk_…`) are limited to a safe, read-mostly set and can never read secrets, change resources, or view billing. See [Publishable keys](#publishable-keys-key-05).

---

## Related documents

- [authentication.md](./authentication.md) — how keys are presented on requests; human/CLI auth.
- [rate-limits.md](./rate-limits.md) — per-key request budgets and `429` handling.
- [security.md](./security.md) — leaked-key handling and encryption.
- [errors.md](./errors.md) — `invalid_api_key`, `insufficient_scope`, `ip_not_allowed`.
