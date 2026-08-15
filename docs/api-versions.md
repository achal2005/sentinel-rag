# API Versions

Meridian versions its REST API so we can improve it without breaking your integrations. This document explains the versioning scheme, how to pin a version, our deprecation policy, and the changelog of notable versions.

---

## Versioning scheme `[ver-01]`

Meridian uses **two layers** of versioning:

1. **Major version in the URL path** — currently `v1`, as in `https://api.meridian.io/v1`. The path version changes only for rare, fundamental redesigns and is supported for years.
2. **Date-based release versions** — a `YYYY-MM-DD` stamp that captures smaller, potentially breaking changes to request/response shapes and behavior. The current stable version is **`2025-08-01`**.

Think of the path (`v1`) as the product generation and the date (`2025-08-01`) as the precise revision within it.

---

## Selecting a version `[ver-02]`

Send the `Meridian-Version` header on every request to pin behavior:

```bash
curl https://api.meridian.io/v1/services \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Meridian-Version: 2025-08-01"
```

Resolution order:

1. The `Meridian-Version` header, if present.
2. Otherwise, your organization's **default version** (see below).
3. Otherwise, the **oldest supported** version — so a brand-new integration that sends no header does not silently ride the latest changes.

Every response echoes the version that served it:

```
Meridian-Version: 2025-08-01
```

---

## Your account's default version `[ver-03]`

The first time your organization makes a successful API call, we **pin your default version** to whatever is current at that moment. This is shown under **Settings → API → Version**. Your default never changes on its own — you upgrade deliberately.

To upgrade the account default, click **Upgrade** on that page and confirm. We recommend testing against the new version by sending the `Meridian-Version` header explicitly from a staging environment first, then flipping the default once you've verified nothing breaks.

---

## What counts as a breaking change `[ver-04]`

We only mint a **new dated version** for changes that could break a well-behaved integration. Breaking changes include:

- Removing or renaming a response field, endpoint, or enum value.
- Changing the type or meaning of an existing field.
- Adding a new **required** request parameter.
- Changing default behavior in a way clients would notice.
- Tightening validation so previously accepted input is now rejected.

The following are **not** breaking and can ship at any time without a version bump, so your integration must tolerate them:

- Adding a new **optional** request parameter.
- Adding a new field to a response object.
- Adding a new endpoint, event type, or enum value to an **output** you don't switch on exhaustively.
- Adding a new webhook event type.
- Changing the wording of human-readable `message` strings in errors (never switch on these — switch on `code`; see [errors.md](./errors.md)).

> **Write forward-compatible clients:** ignore unknown fields, don't assume the enum list is closed, and read pagination via `has_more` rather than counting.

---

## Deprecation policy `[ver-05]`

- When a dated version is deprecated, it remains fully supported for at least **12 months** from the deprecation announcement.
- We announce deprecations on the [changelog](#changelog-ver-07), by email to organization owners and admins, and via the `Meridian-Deprecation` response header on affected calls.
- A deprecated-but-supported version returns a warning header:

  ```
  Meridian-Deprecation: version=2024-02-15; sunset=2025-02-15; link=https://docs.meridian.io/changelog
  ```

- After the sunset date, calls pinned to a removed version fall back to the **oldest still-supported** version and set `Meridian-Version-Fallback: true` so you can detect it in logs.

The **path** version (`v1`) carries a longer guarantee: a minimum of **24 months** of support after a successor path version (e.g. `v2`) becomes generally available.

---

## Checking versions programmatically `[ver-06]`

List the versions your account can use and which one is current:

```bash
curl https://api.meridian.io/v1/versions \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx"
```

```json
{
  "object": "list",
  "current": "2025-08-01",
  "account_default": "2025-02-15",
  "data": [
    { "version": "2025-08-01", "status": "current" },
    { "version": "2025-02-15", "status": "supported" },
    { "version": "2024-11-01", "status": "supported" },
    { "version": "2024-02-15", "status": "deprecated", "sunset": "2025-02-15" }
  ]
}
```

---

## Changelog `[ver-07]`

Notable versions, newest first. The full, continuously updated changelog lives at `https://docs.meridian.io/changelog`.

### `2025-08-01` (current)
- Added `region` to the `service` object and support for the `ap-southeast` (Singapore) region.
- `deployment` objects now include a `health` block with the last health-check result.
- Webhook payloads now include `api_version` so consumers can branch on shape.

### `2025-02-15`
- **Breaking:** `service.status` value `deploying` was split into `building` and `deploying`. Clients that treated `deploying` as "in progress" should now treat both as in progress. See [deployments.md](./deployments.md#deployment-lifecycle-dep-05).
- Added `Idempotency-Key` support to all `POST` endpoints.

### `2024-11-01`
- Added the `/v1/api_keys` endpoints for programmatic key management.
- Added `env:read` / `env:write` scopes.

### `2024-02-15` (deprecated, sunset 2025-02-15)
- Initial public `v1` release.

---

## Frequently asked questions `[ver-08]`

**What happens if I don't send the `Meridian-Version` header?**
We use your organization's pinned **default version**; if you've never called the API, we use the **oldest supported** version so a new integration doesn't silently ride the latest changes. See [Selecting a version](#selecting-a-version-ver-02).

**Will adding a new field to a response break my integration?**
No — additive changes (new fields, new endpoints, new enum values, new event types) are **not** breaking and ship without a version bump. Write tolerant clients that ignore unknown fields. See [What counts as a breaking change](#what-counts-as-a-breaking-change-ver-04).

**How do I upgrade my API version safely?**
Send the new version via the header from a staging environment, verify nothing breaks, then flip your account default under **Settings → API → Version**. See [ver-03](#your-accounts-default-version-ver-03).

**How much notice do I get before a version is removed?**
At least **12 months** from the deprecation announcement for a dated version, with warning headers on affected calls. The `v1` path carries a longer 24-month guarantee. See [Deprecation policy](#deprecation-policy-ver-05).

**How do I see which versions my account can use?**
Call `GET /v1/versions`. See [Checking versions programmatically](#checking-versions-programmatically-ver-06).

---

## Related documents

- [errors.md](./errors.md) — switch on error `code`, never on `message`.
- [webhooks.md](./webhooks.md) — webhook payloads carry `api_version`.
- [deployments.md](./deployments.md) — the `deployment.status` values referenced above.
