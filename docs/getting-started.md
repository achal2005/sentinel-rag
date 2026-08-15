# Getting Started with Meridian

This guide takes you from zero to a live service and your first authenticated API call in about ten minutes. If you only read one document, read this one.

---

## What Meridian is `[start-01]`

Meridian is a **cloud application platform**. You bring code (a web service, an API, a background worker, or a cron job); Meridian builds it, runs it, scales it, and gives it a public URL — without you provisioning servers, load balancers, or TLS certificates.

A typical Meridian setup has three moving parts:

- A **service** — your running application (for example, a Node, Python, Go, or Docker app).
- One or more **managed resources** — a PostgreSQL database, a key-value store, or object storage, attached to the service.
- An **environment** — `production`, `staging`, or an automatically created `preview` environment per pull request.

You manage all of this from the **dashboard** (`https://dashboard.meridian.io`), the **CLI** (`meridian`), or the **REST API** (`https://api.meridian.io/v1`).

---

## Step 1 — Create an account `[start-02]`

1. Go to `https://dashboard.meridian.io/signup`.
2. Sign up with an email and password, or with Google/GitHub single sign-on.
3. Verify your email address by clicking the link we send you. Unverified accounts can browse the dashboard but cannot deploy.
4. When prompted, create your first **organization**. An organization is the top-level container that owns services, billing, and members. You can rename it later under **Settings → Organization**.

New organizations start on the **Hobby** plan, which is free. See [billing.md](./billing.md) for what each plan includes.

---

## Step 2 — Install the CLI `[start-03]`

The CLI is the fastest way to deploy and to stream logs.

```bash
# macOS / Linux
curl -fsSL https://cli.meridian.io/install.sh | sh

# npm (any platform)
npm install -g @meridian/cli

# Homebrew
brew install meridian/tap/meridian
```

Confirm it works and sign in:

```bash
meridian version
meridian login          # opens a browser to authorize the CLI
```

`meridian login` creates a **personal access token** scoped to your user and stores it in `~/.meridian/config.json`. See [authentication.md](./authentication.md#personal-access-tokens-auth-06) for details.

---

## Step 3 — Deploy your first service `[start-04]`

The simplest path is to deploy from a local directory. From the root of a project that has a start command:

```bash
meridian deploy
```

The CLI detects your framework, uploads the code, runs a build, and streams the build logs. When the build passes and the health check succeeds, you get a live URL like `https://sunny-meadow-1234.meridian.app`.

Prefer Git-based deploys? Connect a repository instead:

1. In the dashboard, click **New → Service → Connect a repository**.
2. Authorize GitHub or GitLab and pick the repo and branch.
3. Every push to that branch now triggers an automatic deployment.

Full details, including build configuration and rollbacks, are in [deployments.md](./deployments.md).

---

## Step 4 — Make your first API call `[start-05]`

To use the REST API, create a **secret API key**:

1. Go to **Settings → API Keys** in the dashboard.
2. Click **Create secret key**, give it a name, and copy the value. It starts with `msk_live_` (or `msk_test_` in test mode) and is shown **only once**.

Now list your services:

```bash
curl https://api.meridian.io/v1/services \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx"
```

A successful response looks like:

```json
{
  "object": "list",
  "data": [
    {
      "id": "svc_8Kd02mQ",
      "object": "service",
      "name": "my-first-service",
      "region": "us-east",
      "status": "live",
      "url": "https://sunny-meadow-1234.meridian.app",
      "created_at": "2025-08-01T12:04:11Z"
    }
  ],
  "has_more": false
}
```

Everything you can do in the dashboard, you can do with this API. Read [api-keys.md](./api-keys.md) before putting a key into production, and [rate-limits.md](./rate-limits.md) so you know your request budget.

---

## Step 5 — Get notified of events (optional) `[start-06]`

If you want your own systems to react when a deployment finishes or an invoice is paid, add a **webhook endpoint** under **Settings → Webhooks**. Meridian will POST a signed JSON payload to your URL whenever a subscribed event occurs. See [webhooks.md](./webhooks.md).

---

## Core concepts at a glance `[start-07]`

| Concept | Meaning | Learn more |
|---|---|---|
| Organization | Top-level account that owns everything and pays the bills. | [account-management.md](./account-management.md) |
| Service | A running app: web service, worker, or cron job. | [deployments.md](./deployments.md) |
| Deployment | One build-and-release of a service. | [deployments.md](./deployments.md) |
| Environment | `production`, `staging`, or a `preview` per pull request. | [deployments.md](./deployments.md#environments-dep-08) |
| API key | Credential for the REST API (`msk_…` / `mpk_…`). | [api-keys.md](./api-keys.md) |
| Webhook | A signed event notification sent to your URL. | [webhooks.md](./webhooks.md) |
| Region | Physical location where your service runs. | [deployments.md](./deployments.md#regions-dep-03) |

---

## Where to go next `[start-08]`

- **Securing access:** [authentication.md](./authentication.md) and [api-keys.md](./api-keys.md).
- **Shipping code:** [deployments.md](./deployments.md).
- **Staying within limits:** [rate-limits.md](./rate-limits.md).
- **Understanding your bill:** [billing.md](./billing.md).
- **Something broke:** [troubleshooting.md](./troubleshooting.md) and [errors.md](./errors.md).

If you get stuck, contact `support@meridian.io` or see [support-plans.md](./support-plans.md) for response times.

---

## Frequently asked questions `[start-09]`

**How long does it take to get a service live?**
About ten minutes from signup to a live URL with `meridian deploy`. See [Deploy your first service](#step-3--deploy-your-first-service-start-04).

**Do I need a credit card to start?**
No. The **Hobby** plan is free and requires no payment method. See [billing.md](./billing.md#free-tier-details-bill-03).

**Should I use the dashboard, the CLI, or the API?**
Whichever fits — they're equivalent and produce identical results. Most people click around the dashboard, deploy from the CLI, and automate with the API. See [sdks-and-cli.md](./sdks-and-cli.md).

**What's the difference between an organization and a service?**
An **organization** is your top-level account that owns everything and pays the bills; a **service** is one running app inside it. See [Core concepts](#core-concepts-at-a-glance-start-07).

**Can I deploy straight from GitHub?**
Yes — connect a repository and every push to the tracked branch deploys automatically, with optional preview environments per pull request. See [deployments.md](./deployments.md#ways-to-deploy-dep-01).
