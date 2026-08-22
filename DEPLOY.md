# Deploying Sentinel

Sentinel ships as two container images — the FastAPI **backend** and the Next.js
**operator console** — plus Postgres/pgvector and a local Ollama model server.
`docker-compose.prod.yml` wires them into one self-contained stack.

The default posture is **safe for a public demo**:

- **HTTP Basic auth** guards the whole console and API (`BASIC_AUTH_USER` /
  `BASIC_AUTH_PASS`). The browser is challenged at the Next.js edge; the proxy
  sends the same credentials upstream to the API.
- Only the **frontend (`:3000`) is published**. The API, database, and model
  server stay on the internal Docker network.
- **High-risk tools are simulated** (`TOOLS_SIMULATE=1`): approvals still record
  and return success, but no real n8n webhook fires — so a public demo cannot
  cancel a real invoice.
- **Auth is fail-closed:** the compose file defaults `BASIC_AUTH_*` to
  `admin` / `please-change-me`, so the app is protected out of the box. Change the
  password before exposing it.

## Quick start

```bash
# 1. Configure secrets (at minimum, a strong Basic-auth password).
cp .env.example .env
#   set BASIC_AUTH_USER, BASIC_AUTH_PASS, CORS_ALLOW_ORIGINS in .env

# 2. Build and start everything. First boot pulls the Ollama models
#    (nomic-embed-text + llama3.2:3b) and ingests docs/ — allow a few minutes.
docker compose -f docker-compose.prod.yml up --build -d

# 3. Watch it come up (ollama-init and ingest are one-shot and exit 0).
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

Open <http://localhost:3000> and sign in with your `BASIC_AUTH_*` credentials.

## Required configuration for a public host

| Variable | Why |
|---|---|
| `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` | Gate the console + API. Use a strong password. |
| `CORS_ALLOW_ORIGINS` | Set to the console's public origin (e.g. `https://sentinel.example.com`). |
| `POSTGRES_PASSWORD` | Replace the `sentinel` default. |
| `TOOLS_SIMULATE` | Keep `1` for a demo; set `0` only with a real, sandboxed n8n. |
| `FRONTEND_PORT` | Host port for the console (behind your TLS-terminating reverse proxy). |

Put a reverse proxy (Caddy, nginx, a platform router) in front for **HTTPS** —
Basic auth must only travel over TLS.

## Using Gemini instead of local Ollama

To offload reasoning to Gemini, set in `.env`:

```dotenv
LLM_PROVIDER=gemini
CHAT_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-backend-only-key
EMBED_PROVIDER=ollama          # keep embeddings local and consistent with ingest
```

Keep `EMBED_PROVIDER` unchanged unless you re-ingest — vectors from different
embedding models cannot be mixed. If you switch embeddings to Gemini, re-run the
`ingest` service (`docker compose -f docker-compose.prod.yml run --rm ingest`).

## Hosting the images elsewhere

The images are host-agnostic. Build and push, then run on any platform that takes
a container (Fly.io, Render, a VPS, ECS):

```bash
docker build -f backend/Dockerfile  -t <registry>/sentinel-backend:latest  .
docker build -f frontend/Dockerfile -t <registry>/sentinel-frontend:latest .
```

Provide the same environment variables. The frontend needs `SENTINEL_API_URL`
pointing at the backend and the `BASIC_AUTH_*` pair; the backend needs
`DATABASE_URL`, a model provider (`OLLAMA_HOST` or `GEMINI_API_KEY`), and the same
`BASIC_AUTH_*` pair.

## What is intentionally left out of the demo stack

- **n8n** and **Langfuse** are omitted from `docker-compose.prod.yml`
  (`TOOLS_SIMULATE=1`, `LANGFUSE_ENABLED=0`). Add them back from
  `docker-compose.yml` if you want real tool execution or hosted tracing.
- No autoscaling, rate limiting, or managed secrets — appropriate for a portfolio
  demo, not high-traffic production.
