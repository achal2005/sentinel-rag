# Billing

This document explains Meridian's plans, how usage is metered and priced, how invoices and payments work, and how to manage your billing settings.

Billing questions not answered here can go to `billing@meridian.io`.

---

## Plans `[bill-01]`

| Plan | Price | Included | Best for |
|---|---|---|---|
| **Hobby** | Free | 1 web service, 512 MB RAM, shared CPU, sleeps after inactivity, community support | Side projects, prototypes |
| **Pro** | $19 / member / month | Unlimited services, always-on, custom domains, standard support | Individual developers, small teams |
| **Team** | $99 / month base (includes 5 seats) + usage | SSO, staging + preview environments, priority support, role-based access | Growing teams |
| **Enterprise** | Custom | SCIM, multi-region, SLA, dedicated support, invoicing by PO | Larger orgs with compliance needs |

The plan sets your entitlements (rate limits, environments, support tier). Compute and managed resources are billed **on top** as usage. See [rate-limits.md](./rate-limits.md) and [support-plans.md](./support-plans.md) for what each plan unlocks.

---

## How usage is metered `[bill-02]`

Beyond the plan fee, you pay for what you actually run. Meridian meters:

| Resource | Unit | Notes |
|---|---|---|
| **Compute** | Instance-seconds (by size) | Billed per second while a service instance is running |
| **Bandwidth** | GB egress | Inbound traffic is free; egress is metered |
| **Managed PostgreSQL** | Storage GB-month + compute | Billed per second of runtime plus stored data |
| **Object storage** | GB-month stored + GB egress | |
| **Build minutes** | Minutes | Each plan includes a monthly allotment; overage is metered |

Instance sizes (compute):

| Size | RAM | vCPU |
|---|---|---|
| `starter` | 512 MB | shared |
| `standard` | 1 GB | 1 |
| `standard-2` | 2 GB | 2 |
| `performance` | 4 GB | 4 |

Usage accrues continuously and is visible in near-real-time under **Settings → Billing → Usage**, or via `GET /v1/billing/usage`. `test`-mode resources are **never** billed.

---

## Free tier details `[bill-03]`

The **Hobby** plan is genuinely free, with limits designed for experimentation:

- One always-available web service that **sleeps** after 15 minutes of inactivity and wakes on the next request (expect a short cold-start delay).
- Shared CPU and 512 MB RAM.
- A limited monthly allotment of build minutes and bandwidth; exceeding it pauses new deploys until the next cycle rather than charging you.
- Community support only.

Hobby services do not require a payment method. Adding one and upgrading to Pro removes the sleep behavior and the allotment caps.

---

## Invoices and the billing cycle `[bill-04]`

- Billing runs on a **monthly cycle** starting on the day you first subscribe.
- Plan fees (Pro seats, Team base) are billed **in advance**; usage is billed **in arrears** for the prior period.
- At the end of each cycle Meridian generates an **invoice** combining plan fees + metered usage, charges your default payment method, and emails a receipt.
- Invoices are available under **Settings → Billing → Invoices** as PDF and via `GET /v1/invoices`. Each invoice lists line items per resource.

Invoice lifecycle (also delivered as [webhook events](./webhooks.md#event-catalog-hook-04)):

```
invoice.created → invoice.paid
              └─→ invoice.payment_failed → (retry) → invoice.paid
```

---

## Payment methods `[bill-05]`

- Add a card under **Settings → Billing → Payment methods**. We accept major credit and debit cards.
- **Enterprise** customers can pay by **invoice / bank transfer** against a purchase order with net terms agreed during onboarding.
- The **default** payment method is charged automatically each cycle. You can keep a backup card on file; if the default fails, Meridian tries the backup.
- Card data is handled by our PCI-DSS-compliant payment processor; Meridian never stores full card numbers. See [security.md](./security.md).

---

## Failed payments and dunning `[bill-06]`

If a charge fails, Meridian sends `invoice.payment_failed` and begins **dunning**:

1. We retry the charge on **days 1, 3, 5, and 7** after the failure and email the organization owners each time.
2. Your services keep running during this grace period.
3. If the invoice is still unpaid after **7 days**, non-essential services are **suspended** (`service.suspended` event) until payment succeeds. Your data is retained.
4. If an account remains unpaid for **30 days**, it may be scheduled for deactivation; data deletion follows the retention policy in [security.md](./security.md#data-retention-and-deletion-sec-08).

Update your card promptly to avoid suspension. A suspended service resumes automatically (`service.resumed`) once the outstanding invoice is paid.

---

## Upgrading, downgrading, and cancelling `[bill-07]`

- **Upgrade** anytime under **Settings → Billing → Plan**; the change is immediate and we **prorate** the difference for the remainder of the cycle.
- **Downgrade** takes effect at the **end** of the current cycle so you keep what you've paid for. If your usage exceeds the lower plan's entitlements, you'll be asked to reduce it first (for example, remove extra environments).
- **Adding/removing seats** (Pro, Team) is prorated immediately.
- **Cancel** under **Settings → Billing → Plan → Cancel**. Your account drops to the Hobby tier at the end of the cycle; paid features are disabled and services exceeding Hobby limits are paused. Export anything you need first.

---

## Credits, taxes, and spend controls `[bill-08]`

- **Promotional credits** (e.g. from a program or referral) appear under **Settings → Billing → Credits** and are applied automatically to invoices before your card is charged.
- **Tax** (VAT/GST/sales tax) is calculated based on your billing address; add your **tax ID** under **Settings → Billing → Business info** to have it shown on invoices and, where applicable, reverse-charged.
- **Spend alerts:** set a monthly threshold under **Settings → Billing → Alerts** to get emailed when usage crosses it. Enterprise plans can set **hard caps** that pause new resource creation past a limit.

---

## Viewing billing via the API `[bill-09]`

```bash
# Current period usage
curl https://api.meridian.io/v1/billing/usage \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx"

# List invoices
curl https://api.meridian.io/v1/invoices \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx"
```

Both require the `billing:read` scope. There is no API to *charge* or change payment methods — those actions require a signed-in owner or billing admin in the dashboard for security. See [api-keys.md](./api-keys.md#scopes-and-least-privilege-key-04).

---

## Frequently asked questions `[bill-10]`

**Is the Hobby plan really free?**
Yes. It requires no payment method and is never billed. Services sleep after 15 minutes of inactivity and wake on the next request. See [Free tier details](#free-tier-details-bill-03).

**My services were suspended. How do I get them back?**
Suspension almost always follows an unpaid invoice after the 7-day dunning window. Update your card under **Settings → Billing**; suspended services resume automatically once the invoice is paid. See [Failed payments and dunning](#failed-payments-and-dunning-bill-06).

**Why is my bill higher than the plan price?**
The plan fee is on top of **metered usage** — compute instance-seconds, bandwidth egress, managed data, and build minutes. Check **Settings → Billing → Usage** and set spend alerts. See [How usage is metered](#how-usage-is-metered-bill-02).

**Can I pay by invoice or purchase order instead of a card?**
Yes, on the **Enterprise** plan with net terms agreed during onboarding. See [Payment methods](#payment-methods-bill-05).

**What happens when I downgrade?**
Downgrades take effect at the **end** of the current cycle so you keep what you paid for; if your usage exceeds the lower plan's limits, you'll be asked to reduce it first. See [Upgrading, downgrading, and cancelling](#upgrading-downgrading-and-cancelling-bill-07).

**Can I set a hard spending cap?**
Spend **alerts** are available on all paid plans; **hard caps** that pause new resource creation are an Enterprise feature. See [Credits, taxes, and spend controls](#credits-taxes-and-spend-controls-bill-08).

---

## Related documents

- [account-management.md](./account-management.md) — who can see and change billing (roles).
- [support-plans.md](./support-plans.md) — support level included with each plan.
- [rate-limits.md](./rate-limits.md) — plan-based API limits.
- [security.md](./security.md) — payment data handling and data retention.
