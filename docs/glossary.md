# Glossary

Definitions of terms used throughout the Meridian documentation. Each entry links to the doc that covers it in depth.

---

## A–C `[gloss-01]`

**API key** — A credential used to authenticate requests to the Meridian REST API. Secret keys (`msk_…`) authenticate servers; publishable keys (`mpk_…`) identify an account in front-end code. See [api-keys.md](./api-keys.md).

**API version** — A dated (`YYYY-MM-DD`) revision of the API, sent via the `Meridian-Version` header, that pins request/response behavior. See [api-versions.md](./api-versions.md).

**Audit log** — A record of administrative actions (member, key, policy, billing changes) available on Team/Enterprise plans. See [account-management.md](./account-management.md#audit-log-acct-09).

**Bandwidth** — Network egress from your services, metered and billed by the GB. See [billing.md](./billing.md#how-usage-is-metered-bill-02).

**Bearer authentication** — Sending a key as `Authorization: Bearer <key>`. Meridian's API auth method. See [authentication.md](./authentication.md#authenticating-api-requests-auth-05).

**Build** — The stage where Meridian compiles/packages your code into an immutable image before release. See [deployments.md](./deployments.md#build-pipeline-dep-02).

**CLI** — The `meridian` command-line tool for deploying and managing resources. See [sdks-and-cli.md](./sdks-and-cli.md).

**Cron job** — A service type that runs on a schedule and then exits. See [deployments.md](./deployments.md#service-types-dep-04).

---

## D–H `[gloss-02]`

**Deployment** — A single build-and-release of a service, with a lifecycle from `queued` to `live`. See [deployments.md](./deployments.md#deployment-lifecycle-dep-05).

**Dunning** — The retry-and-notify process after a failed payment, before suspension. See [billing.md](./billing.md#failed-payments-and-dunning-bill-06).

**Environment** — An isolated instance of a service (`production`, `staging`, `preview`) with its own variables and URL. See [deployments.md](./deployments.md#environments-dep-08).

**Environment variable** — A configuration value injected into a service; can be marked **secret** (write-only). See [deployments.md](./deployments.md#build-pipeline-dep-02).

**Event** — A record that something happened in your account, delivered to webhook endpoints. See [webhooks.md](./webhooks.md#event-object-hook-03).

**Health check** — The check Meridian runs before shifting traffic to a new deployment. See [deployments.md](./deployments.md#health-checks-dep-06).

---

## I–O `[gloss-03]`

**Idempotency key** — A client-supplied header (`Idempotency-Key`) that makes a `POST` safe to retry without duplicating the effect. See [webhooks.md](./webhooks.md#idempotency-hook-06).

**Instance** — A single running copy of a service; compute is billed by instance-seconds and size. See [billing.md](./billing.md#how-usage-is-metered-bill-02).

**Managed resource** — A Meridian-operated primitive (PostgreSQL, key-value store, object storage) attached to your services. See [getting-started.md](./getting-started.md#what-meridian-is-start-01).

**MFA (multi-factor authentication)** — A second sign-in factor (TOTP or WebAuthn). See [authentication.md](./authentication.md#multi-factor-authentication-mfa-auth-03).

**Organization** — The top-level account that owns services, billing, and members. See [account-management.md](./account-management.md#the-account-model-acct-01).

**OAuth 2.0** — The mechanism for third-party apps to act on behalf of Meridian users without their keys. See [authentication.md](./authentication.md#oauth-for-third-party-apps-auth-07).

---

## P–R `[gloss-04]`

**Personal access token (PAT)** — A token (`mpat_…`) that authenticates an individual user from the CLI or scripts. See [authentication.md](./authentication.md#personal-access-tokens-auth-06).

**Preview environment** — A temporary environment created automatically per pull request. See [deployments.md](./deployments.md#environments-dep-08).

**Publishable key** — A front-end-safe key (`mpk_…`) with a limited, read-mostly capability set. See [api-keys.md](./api-keys.md#publishable-keys-key-05).

**Rate limit** — The cap on API requests per key per window; exceeding it returns `429`. See [rate-limits.md](./rate-limits.md).

**Region** — The physical location where a service runs (`us-east`, `eu-central`, etc.). See [deployments.md](./deployments.md#regions-dep-03).

**Request ID** — A unique identifier (`req_…`) on every API response, used for support and debugging. See [errors.md](./errors.md#error-response-format-err-01).

**Rollback** — Restoring a previous deployment's image, instantly and safely. See [deployments.md](./deployments.md#rollbacks-dep-09).

**Role** — A permission set (Owner, Admin, Developer, Billing, Viewer) assigned to a member. See [account-management.md](./account-management.md#roles-and-permissions-acct-02).

---

## S–Z `[gloss-05]`

**Scope** — A `resource:action` permission attached to an API key (e.g. `deployments:write`). See [api-keys.md](./api-keys.md#scopes-and-least-privilege-key-04).

**SCIM** — A protocol for automatically provisioning/deprovisioning members from your IdP (Enterprise). See [authentication.md](./authentication.md#single-sign-on-sso-auth-04).

**Secret key** — A server-side API key (`msk_…`) that must be kept confidential. See [api-keys.md](./api-keys.md#key-types-key-01).

**Service** — A running application on Meridian: web service, worker, cron, or static site. See [deployments.md](./deployments.md#service-types-dep-04).

**Signing secret** — The `whsec_…` value used to verify webhook signatures. See [webhooks.md](./webhooks.md#verifying-signatures-hook-05).

**SLA** — A contractual service-level commitment (uptime and/or support response). See [support-plans.md](./support-plans.md#service-level-agreement-sla-sup-05).

**SSO (single sign-on)** — Signing in through your company's identity provider via SAML. See [authentication.md](./authentication.md#single-sign-on-sso-auth-04).

**Suspension** — Pausing services (e.g. for non-payment) while retaining data. See [billing.md](./billing.md#failed-payments-and-dunning-bill-06).

**Team** — A named group of members with shared access to specific services (Team/Enterprise). See [account-management.md](./account-management.md#teams-acct-05).

**Test mode** — An isolated sandbox using `…_test_…` keys; never billed, separate limits. See [api-keys.md](./api-keys.md#key-types-key-01).

**Webhook** — A signed HTTP callback Meridian sends to your endpoint when an event occurs. See [webhooks.md](./webhooks.md).

**Zero-downtime deploy** — A rolling release that shifts traffic only after the new version is healthy. See [deployments.md](./deployments.md#zero-downtime-releases-dep-07).

---

## Related documents

- [README.md](./README.md) — documentation index and citation-ID convention.
- [getting-started.md](./getting-started.md) — concepts in context.
