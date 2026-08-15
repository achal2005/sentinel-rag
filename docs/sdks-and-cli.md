# SDKs and CLI

Meridian provides official client libraries and a command-line tool so you don't hand-roll HTTP calls, signatures, and retry logic. This document lists what's available and shows the common patterns.

---

## Official SDKs `[sdk-01]`

| Language | Package | Install |
|---|---|---|
| Node.js / TypeScript | `@meridian/sdk` | `npm install @meridian/sdk` |
| Python | `meridian` | `pip install meridian` |
| Go | `github.com/meridian/meridian-go` | `go get github.com/meridian/meridian-go` |
| Ruby | `meridian` | `gem install meridian` |

All official SDKs share the same conventions:

- **Automatic retries** with exponential backoff on `429`/`500`/`503`, honoring `Retry-After`. See [rate-limits.md](./rate-limits.md).
- **Built-in webhook signature verification.** See [webhooks.md](./webhooks.md#verifying-signatures-hook-05).
- **Typed errors** mapped from the API's `type`/`code`. See [errors.md](./errors.md).
- **Version pinning** via a client option that sets the `Meridian-Version` header. See [api-versions.md](./api-versions.md).
- **Idempotency** helpers that attach an `Idempotency-Key` to writes.

---

## Quick examples `[sdk-02]`

**Node.js / TypeScript**
```ts
import { Meridian } from "@meridian/sdk";

const meridian = new Meridian({
  apiKey: process.env.MERIDIAN_API_KEY, // msk_live_...
  version: "2025-08-01",
});

const services = await meridian.services.list();

const deployment = await meridian.deployments.create(
  "svc_8Kd02mQ",
  { gitRef: "main" },
  { idempotencyKey: "deploy-2025-08-01-a" }
);
```

**Python**
```python
from meridian import Meridian

client = Meridian(api_key="msk_live_...", version="2025-08-01")

services = client.services.list()

deployment = client.deployments.create(
    "svc_8Kd02mQ",
    git_ref="main",
    idempotency_key="deploy-2025-08-01-a",
)
```

**Verifying a webhook (Python)**
```python
from meridian.webhooks import verify, InvalidSignature

@app.post("/hooks/meridian")
async def hook(request):
    raw = await request.body()
    try:
        event = verify(raw, request.headers["Meridian-Signature"], secret=WHSEC)
    except InvalidSignature:
        return Response(status_code=400)
    # handle event.type ...
    return Response(status_code=200)
```

---

## Handling errors with the SDK `[sdk-03]`

SDKs raise typed exceptions you can catch by category:

```python
from meridian import RateLimitError, AuthenticationError, MeridianError

try:
    client.services.list()
except RateLimitError as e:
    # already retried automatically; only reached if retries exhausted
    ...
except AuthenticationError:
    ...
except MeridianError as e:
    log.error("meridian error", code=e.code, request_id=e.request_id)
```

Every exception exposes `code`, `type`, `message`, and `request_id` — include `request_id` in support tickets. See [errors.md](./errors.md).

---

## The `meridian` CLI `[sdk-04]`

Install (see [getting-started.md](./getting-started.md#step-2--install-the-cli-start-03)):

```bash
curl -fsSL https://cli.meridian.io/install.sh | sh   # macOS/Linux
npm install -g @meridian/cli                          # any platform
```

Authenticate:
```bash
meridian login    # browser-based; creates a personal access token
```

Common commands:

| Command | Does |
|---|---|
| `meridian deploy` | Deploy the current directory to the linked service |
| `meridian services list` | List services |
| `meridian logs --service <id> --follow` | Stream runtime logs |
| `meridian logs --build` | Stream build logs |
| `meridian rollback --service <id>` | Roll back to the previous deployment |
| `meridian env set KEY=value --env production` | Set an environment variable |
| `meridian env pull > .env` | Download env vars for local use |
| `meridian open` | Open the current service in the dashboard |
| `meridian whoami` | Show the authenticated user and org |

`--json` on most commands prints machine-readable output for scripting. Global flags: `--org <slug>` to target an org, `--env <name>` to target an environment.

---

## CLI authentication in CI `[sdk-05]`

Don't use `meridian login` (interactive) in CI. Instead, set an **organization API key** as an environment variable:

```bash
export MERIDIAN_API_KEY=msk_live_xxxxxxxxxxxxxxxxxxxx
meridian deploy --service svc_8Kd02mQ --env production
```

Use a **scoped** key (e.g. `deployments:write`) and store it in your CI secrets manager, never in the repo. See [api-keys.md](./api-keys.md#scopes-and-least-privilege-key-04). Prefer an org key over a personal access token so pipelines don't break when a person leaves.

---

## Versioning and upgrades `[sdk-06]`

- SDKs follow **semantic versioning**. Breaking changes bump the major version.
- Pin the **API version** (`Meridian-Version`) explicitly in your client config so upgrading the SDK doesn't silently change API behavior. See [api-versions.md](./api-versions.md#selecting-a-version-ver-02).
- SDK release notes link the API versions they default to. Upgrade the SDK and the API version deliberately, testing in staging first.

---

## Community libraries `[sdk-07]`

Community-maintained libraries exist for other languages (PHP, Rust, .NET). They are **not** covered by Meridian support SLAs and may lag the API. For production use we recommend an official SDK or direct HTTP calls against the documented, versioned API.

---

## Frequently asked questions `[sdk-08]`

**Do the SDKs retry rate-limited requests for me?**
Yes. Official SDKs retry `429`/`500`/`503` with exponential backoff and honor `Retry-After` by default. See [Official SDKs](#official-sdks-sdk-01).

**How should I authenticate the CLI in CI?**
Don't use interactive `meridian login`. Set an **organization API key** as `MERIDIAN_API_KEY` (scoped, from your CI secrets) and the CLI/SDK picks it up. See [CLI authentication in CI](#cli-authentication-in-ci-sdk-05).

**Which languages have official SDKs?**
Node/TypeScript, Python, Go, and Ruby. Community libraries exist for others but aren't covered by support SLAs. See [Official SDKs](#official-sdks-sdk-01) and [Community libraries](#community-libraries-sdk-07).

**Will upgrading the SDK change the API behavior I see?**
Not if you **pin the API version** in your client config. Upgrade the SDK and the API version deliberately, testing in staging. See [Versioning and upgrades](#versioning-and-upgrades-sdk-06).

**How do I verify webhooks without implementing HMAC myself?**
Use the built-in `meridian.webhooks.verify(...)` helper. See [Quick examples](#quick-examples-sdk-02) and [webhooks.md](./webhooks.md#verifying-signatures-hook-05).

---

## Related documents

- [getting-started.md](./getting-started.md) — install and first calls.
- [webhooks.md](./webhooks.md) — signature verification helpers.
- [rate-limits.md](./rate-limits.md) — built-in retry behavior.
- [errors.md](./errors.md) — typed error handling.
