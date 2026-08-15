# Support Plans

This document describes how to get help from Meridian, the support tier included with each plan, target response times, and what to include so we can help you fast.

---

## Support channels `[sup-01]`

| Channel | Use for | Availability |
|---|---|---|
| **Documentation** (`docs.meridian.io`) | Self-service answers | Always |
| **Community forum** (`community.meridian.io`) | Questions, tips, discussion | Always |
| **Status page** (`status.meridian.io`) | Incident and maintenance updates | Always |
| **Email** (`support@meridian.io`) | Account-specific problems | Per plan (below) |
| **In-dashboard widget** | The fastest way to file a ticket with context attached | Per plan |
| **Security** (`security@meridian.io`) | Vulnerabilities, suspected compromise | Always, prioritized |

Always check the **status page** first — if there's an active incident, the answer may already be there. See [troubleshooting.md](./troubleshooting.md).

---

## Support tiers by plan `[sup-02]`

| Plan | Tier | Channels | Target first response |
|---|---|---|---|
| **Hobby** | Community | Docs, forum | Best-effort (community) |
| **Pro** | Standard | Email, dashboard | 1 business day |
| **Team** | Priority | Email, dashboard | 4 business hours |
| **Enterprise** | Premier | Email, dashboard, dedicated contact, optional Slack | 1 hour for urgent (24×7) |

"Business hours/days" are Monday–Friday, 09:00–18:00 in your account's configured timezone, excluding public holidays. Enterprise urgent coverage is **24×7**. These are **first-response** targets, not resolution times.

---

## Severity levels `[sup-03]`

When you file a ticket, pick a severity. It sets priority and, on paid plans, the response target.

| Severity | Definition | Examples |
|---|---|---|
| **S1 — Critical** | Production down or major data risk, no workaround | All services returning errors; suspected data breach |
| **S2 — High** | Significant impairment, workaround exists | Deploys failing repeatedly; webhooks not delivering |
| **S3 — Normal** | Minor or partial impact | A single non-critical error; confusing behavior |
| **S4 — Low** | Question, guidance, or feature request | "How do I…"; docs feedback |

The response targets in [§sup-02](#support-tiers-by-plan-sup-02) apply to **S1/S2** on paid tiers. Set severity honestly — over-escalating slows everyone down; under-escalating a real outage delays help.

---

## What to include in a ticket `[sup-04]`

Give us enough to reproduce and locate the problem on the first reply:

- **`request_id`** from the error response (`req_…`) — the single most useful item.
- **Resource IDs:** service (`svc_…`), deployment (`dep_…`), or key (`key_…`, never the secret).
- **Timestamp (UTC)** of the problem.
- **What you expected** vs. **what happened**, and the exact error `code`/`message`.
- **Steps to reproduce**, and whether it's consistent or intermittent.
- The **environment** (`production` / `staging` / `preview`) and **region**.

Never paste secret keys, passwords, or full webhook signing secrets into a ticket — share only the `last4` of a key if needed. See [api-keys.md](./api-keys.md#keeping-keys-secret-key-09).

---

## Service level agreement (SLA) `[sup-05]`

- **Uptime commitment:** Enterprise plans include a contractual uptime SLA (typically **99.9%** monthly for production services) with service credits if we miss it. Terms are in your order form.
- **Hobby, Pro, and Team** are provided on a commercially reasonable best-effort basis without a contractual uptime credit, though we publish real-time and historical uptime at `https://status.meridian.io`.
- **Support-response SLAs** apply to Team (Priority) and Enterprise (Premier) as in [§sup-02](#support-tiers-by-plan-sup-02). Community and Standard tiers have *targets*, not contractual SLAs.

Request the full SLA and uptime history from your account team or `support@meridian.io`.

---

## Incidents and status `[sup-06]`

- Live incident and maintenance updates: `https://status.meridian.io`. Subscribe there for email/SMS/webhook notifications.
- During an incident we post regular updates until resolution, followed by a **post-incident review** for significant events.
- If you're seeing errors, check the status page before filing — if it's a known incident, you don't need to open a ticket, though Enterprise customers may still contact their dedicated contact for impact assessment.

---

## Upgrading your support `[sup-07]`

- Support tier follows your **plan** — upgrade the plan to raise your tier (see [billing.md](./billing.md#upgrading-downgrading-and-cancelling-bill-07)).
- **Enterprise** add-ons (dedicated contact, Slack channel, custom SLA, onboarding assistance) are arranged with the sales team.
- Community support is available to everyone, including Hobby, via `community.meridian.io`.

---

## Frequently asked questions `[sup-08]`

**What's the target response time on the Pro plan?**
Standard support with a **1 business day** first-response target via email and the dashboard widget. See [Support tiers by plan](#support-tiers-by-plan-sup-02).

**Does Meridian offer an uptime SLA?**
A contractual uptime SLA (typically 99.9% monthly for production) is an **Enterprise** feature; other plans are best-effort with public status history at `status.meridian.io`. See [Service level agreement](#service-level-agreement-sla-sup-05).

**What should I include when I open a ticket?**
The `request_id`, relevant resource IDs (`svc_…`, `dep_…`), the UTC timestamp, the exact error `code`/`message`, and steps to reproduce. Never paste secret keys. See [What to include in a ticket](#what-to-include-in-a-ticket-sup-04).

**How do I raise my support tier?**
Support tier follows your **plan** — upgrade the plan, or arrange Enterprise add-ons with sales. See [Upgrading your support](#upgrading-your-support-sup-07).

**There's an incident — do I still need to open a ticket?**
Check `status.meridian.io` first; if it's a known incident you don't need to file one, though Enterprise customers can contact their dedicated contact for impact assessment. See [Incidents and status](#incidents-and-status-sup-06).

---

## Related documents

- [troubleshooting.md](./troubleshooting.md) — solve it yourself first.
- [errors.md](./errors.md) — find the `request_id` and error `code`.
- [billing.md](./billing.md) — plans that determine your tier.
- [security.md](./security.md) — reporting vulnerabilities and compromise.
