# Sentinel frontend

The Next.js operator console for Sentinel. The interface is intentionally evidence-first: values are read from the FastAPI runtime, Postgres run history, approval queue, and the latest generated eval report.

## Views

- `/` — product overview with the latest eval summary and live runtime configuration
- `/inbox` — persisted graph runs
- `/requests/[id]` — one run's route, cost, citations, and audit trail
- `/approvals` — pending high-risk n8n actions
- `/usage` — live cost/latency breakdowns and the generated eval report
- `/console` — submit a request to the live graph

## Run locally

Start the FastAPI service on port `8000`, then run:

```bash
npm install
npm run dev
```

The browser-facing code calls same-origin route handlers under `/api`. Those handlers proxy to `SENTINEL_API_URL` (default `http://localhost:8000`) so backend addresses and CORS details stay server-side.

## Verification

```bash
npm run lint
npm run build
```

The UI does not fall back to sample traffic or invented metrics. When the backend is unavailable, runtime values remain unknown and the interface shows an explicit offline state; the eval panel can still read `evals/reports/latest.json` from the repository.
