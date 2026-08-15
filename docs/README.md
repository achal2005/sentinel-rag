# Meridian Documentation

Welcome to the official documentation for the **Meridian Platform** — the cloud application platform that lets teams deploy backend services, APIs, and managed data without running their own servers.

> **Ship backend services without managing servers.**

This directory is the complete public documentation set. It is the knowledge base for Meridian's support, onboarding, and developer-experience teams.

---

## Product overview

Meridian gives developers three things:

1. **Deployments** — push code (via Git or the CLI) and Meridian builds, deploys, health-checks, and serves it across managed regions with zero-downtime rollouts and one-click rollbacks.
2. **The Meridian API** — a REST control-plane API (`https://api.meridian.io/v1`) for managing everything you can do in the dashboard: services, deployments, environment variables, members, and billing.
3. **Managed primitives** — managed PostgreSQL, key-value stores, object storage, cron jobs, and background workers that attach to your services.

Everything is available in the **dashboard** (`https://dashboard.meridian.io`), through the **API**, and through the **CLI** (`meridian`).

---

## Key resources

| Resource | URL |
|---|---|
| Dashboard | `https://dashboard.meridian.io` |
| API base URL | `https://api.meridian.io/v1` |
| Documentation | `https://docs.meridian.io` |
| Status page | `https://status.meridian.io` |
| Support | `support@meridian.io` |
| Billing | `billing@meridian.io` |
| Security / vulnerability reports | `security@meridian.io` |

---

## Documentation index

| Doc | What it covers |
|---|---|
| [getting-started.md](./getting-started.md) | Create an account, deploy your first service, make your first API call. |
| [authentication.md](./authentication.md) | Logging in, SSO, MFA, personal access tokens, and authenticating API requests. |
| [api-keys.md](./api-keys.md) | Creating, scoping, rotating, and revoking secret and publishable API keys. |
| [api-versions.md](./api-versions.md) | The date-based versioning scheme, deprecation policy, and changelog. |
| [deployments.md](./deployments.md) | Git and CLI deploys, build pipeline, environments, rollbacks, health checks. |
| [webhooks.md](./webhooks.md) | Subscribing to events, verifying signatures, retries, and idempotency. |
| [rate-limits.md](./rate-limits.md) | API rate limits per plan, headers, and handling `429` responses. |
| [billing.md](./billing.md) | Plans, pricing, usage metering, invoices, and payment methods. |
| [account-management.md](./account-management.md) | Organizations, teams, members, roles, and account lifecycle. |
| [security.md](./security.md) | Data protection, compliance, encryption, and responsible disclosure. |
| [troubleshooting.md](./troubleshooting.md) | Diagnosing common problems across auth, deploys, webhooks, and billing. |
| [errors.md](./errors.md) | Canonical HTTP status codes and error-code reference. |
| [sdks-and-cli.md](./sdks-and-cli.md) | Official client libraries and the `meridian` CLI. |
| [support-plans.md](./support-plans.md) | Support tiers, response-time SLAs, and how to reach a human. |
| [glossary.md](./glossary.md) | Definitions of Meridian terms used throughout the docs. |

---

## Citation IDs (read this if you are indexing these docs)

Every major section heading ends with a **stable citation ID** in square brackets, for example:

> ## Regenerating a secret key `[key-06]`

These IDs are **stable** — we do not reuse or renumber them when content is edited. They exist so automated systems (support agents, RAG pipelines, internal tools) can cite an exact section, e.g.:

> "You can regenerate a secret key from the dashboard under **Settings → API Keys** `[key-06]`."

Prefix map:

| Prefix | Document |
|---|---|
| `start-` | getting-started.md |
| `auth-` | authentication.md |
| `key-` | api-keys.md |
| `ver-` | api-versions.md |
| `dep-` | deployments.md |
| `hook-` | webhooks.md |
| `rate-` | rate-limits.md |
| `bill-` | billing.md |
| `acct-` | account-management.md |
| `sec-` | security.md |
| `ts-` | troubleshooting.md |
| `err-` | errors.md |
| `sdk-` | sdks-and-cli.md |
| `sup-` | support-plans.md |
| `gloss-` | glossary.md |

---

## Conventions used throughout

- **Base URL** for every API example is `https://api.meridian.io/v1`.
- Code samples use `curl` unless a language is specified.
- Placeholder secrets are shown as `msk_live_xxxxxxxxxxxxxxxxxxxx` and should never be committed to source control.
- `test`-mode identifiers (`msk_test_…`, `mpk_test_…`) never touch production data or billing.
- Times are ISO 8601 / UTC unless stated otherwise.

_Last reviewed: 2025-08-01 · API version `2025-08-01`._
