# Deployments

A **deployment** is a single build-and-release of a service. This document covers the ways to deploy, the build pipeline, regions, the deployment lifecycle, environments, health checks, rollbacks, and zero-downtime releases.

---

## Ways to deploy `[dep-01]`

There are three ways to ship code to Meridian. They produce identical deployments.

| Method | Best for | How |
|---|---|---|
| **Git integration** | Teams, continuous deployment | Connect GitHub/GitLab; every push to the tracked branch deploys |
| **CLI** | Local development, scripts | `meridian deploy` from your project directory |
| **REST API** | Custom pipelines | `POST /v1/services/{id}/deployments` |

### Git integration
In the dashboard: **New → Service → Connect a repository**, authorize the provider, pick the repo and branch. Each push triggers a build. Pull requests can spin up **preview environments** automatically (see [Environments](#environments-dep-08)).

### CLI
From a project directory:
```bash
meridian deploy                 # deploy current directory to the linked service
meridian deploy --service svc_8Kd02mQ
meridian logs --service svc_8Kd02mQ --follow
```

### API
```bash
curl https://api.meridian.io/v1/services/svc_8Kd02mQ/deployments \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: deploy-2025-08-01-a" \
  -d '{ "git_ref": "main" }'
```

Always send an `Idempotency-Key` on deploy requests so a retry never starts two builds. See [webhooks.md](./webhooks.md#idempotency-hook-06) for the idempotency model.

---

## Build pipeline `[dep-02]`

Every deployment runs through the same stages:

1. **Fetch** — Meridian pulls your source (from Git or the uploaded archive).
2. **Detect / Build** — Meridian auto-detects common frameworks (Node, Python, Go, Ruby, Rust, static sites) and builds them. If a `Dockerfile` is present, Meridian builds the image instead. You can override the build and start commands under **Settings → Build**.
3. **Package** — the result is stored as an immutable image tagged with the deployment ID.
4. **Release** — the image is rolled out to your service's region(s) behind the load balancer.
5. **Health check** — Meridian waits for the new instances to pass their health check before shifting traffic (see [Health checks](#health-checks-dep-06)).

Build configuration you'll commonly set:

- **Build command** — e.g. `npm run build`.
- **Start command** — e.g. `node server.js`. The service must listen on the port given by the `PORT` environment variable.
- **Environment variables** — set under **Settings → Environment**, or via `env:write` on the API. Changing an env var triggers a new deployment.
- **Build settings** — Node version, root directory (for monorepos), and cache behavior.

Build logs stream live in the dashboard and via `meridian logs --build`.

---

## Regions `[dep-03]`

Choose the region closest to your users when you create a service. A service runs in exactly one region unless you're on Enterprise multi-region.

| Region code | Location |
|---|---|
| `us-east` | Virginia, USA |
| `us-west` | Oregon, USA |
| `eu-central` | Frankfurt, Germany |
| `ap-south` | Mumbai, India |
| `ap-southeast` | Singapore |

You cannot change a service's region in place; to move, create a new service in the target region and cut over DNS. Managed databases should live in the **same region** as the services that use them to keep latency low.

---

## Service types `[dep-04]`

| Type | Description | Gets a URL? |
|---|---|---|
| **Web service** | Handles HTTP traffic; autoscaled behind a load balancer | Yes |
| **Background worker** | Long-running process, no inbound traffic (queues, consumers) | No |
| **Cron job** | Runs on a schedule you define, then exits | No |
| **Static site** | Pre-built assets served from the edge CDN | Yes |

Web services and static sites receive a `*.meridian.app` URL automatically and support custom domains with managed TLS (**Settings → Domains**).

---

## Deployment lifecycle `[dep-05]`

A deployment moves through these statuses (the `deployment.status` field):

```
queued → building → deploying → live
                        │
                        ├── failed        (build or health check failed)
                        ├── canceled      (you canceled it)
                        └── rolled_back    (superseded by a rollback)
```

- **queued** — waiting for a build slot.
- **building** — running your build command / building the image.
- **deploying** — rolling the new image out and running health checks.
- **live** — serving traffic. Only one deployment per environment is `live` at a time.
- **failed** — see the build/health logs; traffic stays on the previous `live` deployment.
- **canceled** — stopped before completion; no traffic change.
- **rolled_back** — a previously live deployment that has been replaced by a rollback.

> Prior to API version `2025-02-15`, `building` and `deploying` were a single `deploying` status. See [api-versions.md](./api-versions.md#changelog-ver-07).

Failed deployments **never** take down your running service — traffic only shifts after the new version is healthy. This is the core safety property of the platform.

---

## Health checks `[dep-06]`

Before a new deployment receives traffic, Meridian verifies it is healthy.

- **Default:** Meridian checks that your service accepts TCP connections on `PORT`.
- **HTTP health check (recommended):** set a path such as `/healthz` under **Settings → Health Check**. Meridian sends `GET /healthz` and expects a `2xx` response.
- **Timing:** by default Meridian retries the check for up to **90 seconds** after the service starts. If it never passes, the deployment is marked `failed` and traffic stays on the previous version.

A good health endpoint returns `200` only when the app can actually serve requests (dependencies connected, migrations applied). A health check that always returns `200` defeats the purpose.

---

## Zero-downtime releases `[dep-07]`

Web services deploy with a **rolling release**:

1. New instances start alongside the old ones.
2. New instances must pass the health check.
3. The load balancer shifts traffic to the new instances.
4. Old instances drain in-flight requests, then stop.

To make this safe for your users:

- Ensure your app handles `SIGTERM` and finishes in-flight requests within the **30-second** drain window.
- Keep database migrations **backward-compatible** so old and new versions can run simultaneously for a few seconds.
- Don't rely on in-memory state surviving a deploy; use a managed store.

---

## Environments `[dep-08]`

A service can have multiple **environments**, each with its own URL, environment variables, and deployment history.

| Environment | Purpose | How it's created |
|---|---|---|
| `production` | Live traffic | Default; deploys from your production branch |
| `staging` | Pre-production testing | You create it and point it at a branch |
| `preview` | Per-pull-request testing | Created automatically for each open PR when previews are enabled |

- **Environment variables** are scoped per environment. A variable can be marked **secret**, in which case its value is write-only (you can set it but never read it back) and is redacted in logs.
- **Preview environments** are torn down automatically when the pull request is closed or merged.
- Promote a tested build from `staging` to `production` with **Promote** in the dashboard, or `POST /v1/services/{id}/promote` — this reuses the exact image, so what you tested is what ships.

---

## Rollbacks `[dep-09]`

Every successful deployment is retained as an immutable image, so rolling back is instant and safe.

- **Dashboard:** open the service's **Deployments** tab, find a previous `live` deployment, and click **Rollback**.
- **CLI:** `meridian rollback --service svc_8Kd02mQ`.
- **API:** `POST /v1/services/{id}/deployments/{deployment_id}/rollback`.

A rollback creates a new deployment that reuses the older image and goes through the normal health-check and traffic-shift process. The deployment you rolled back *from* is marked `rolled_back`. Rollbacks do **not** revert environment-variable or database changes — only the application image — so be careful when a bad deploy also ran an incompatible migration.

---

## Deployment notifications `[dep-10]`

Subscribe to deployment events to drive your own automation (Slack messages, changelog updates, smoke tests):

- `deployment.created`
- `deployment.succeeded`
- `deployment.failed`
- `deployment.rolled_back`

Configure these under **Settings → Webhooks**. Payloads and signature verification are documented in [webhooks.md](./webhooks.md).

---

## Frequently asked questions `[dep-11]`

**Will a failed deployment take down my running service?**
No. Traffic only shifts to a new deployment **after** it passes its health check. A failed build or health check leaves the previous version live. See [Deployment lifecycle](#deployment-lifecycle-dep-05).

**Can I change a service's region after creating it?**
No. Create a new service in the target region and cut over DNS. Keep managed databases in the **same region** as the services that use them. See [Regions](#regions-dep-03).

**My deploy succeeded but the app returns 502. Why?**
Usually the process crashes on start or listens on the wrong port. Bind to the `PORT` env var and `0.0.0.0`, and confirm required environment variables are set **for that environment**. See [Health checks](#health-checks-dep-06) and [troubleshooting.md](./troubleshooting.md#deployment-failures-ts-03).

**Does a rollback also undo my database migration?**
No. A rollback restores the **application image only** — not environment variables or database changes. Be careful when a bad deploy also ran an incompatible migration. See [Rollbacks](#rollbacks-dep-09).

**How do preview environments get cleaned up?**
Automatically — a preview environment is torn down when its pull request is closed or merged. See [Environments](#environments-dep-08).

**How do I promote a tested build to production?**
Use **Promote**, which reuses the exact image you tested, so what you verified is what ships. See [Environments](#environments-dep-08).

---

## Related documents

- [webhooks.md](./webhooks.md) — deployment event payloads and idempotency.
- [api-versions.md](./api-versions.md) — the `building`/`deploying` status split.
- [troubleshooting.md](./troubleshooting.md) — diagnosing failed builds and health checks.
- [rate-limits.md](./rate-limits.md) — deploy-trigger limits.
