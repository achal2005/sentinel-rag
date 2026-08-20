# n8n: Webhook → tickets

A minimal workflow that accepts an HTTP POST and inserts a row into the `tickets`
table in the project's Postgres.

> **Port:** Sentinel's n8n is published on host port **5679** (container port
> stays 5678). Port 5678 is deliberately avoided because another local n8n often
> already owns it — if you map to 5678 and something else has it, your `curl`s
> silently hit the *other* n8n and you get spurious 404s. Override with
> `N8N_HOST_PORT` in `.env` if 5679 is also taken.

## 1. Create the table

```bash
docker compose exec -T db psql -U sentinel -d sentinel < n8n/tickets.sql
```

(The app also creates this table automatically via `backend/app/db.py`'s schema.)

## 2. Create the Postgres credential in n8n

Open http://localhost:5679 → **Credentials → New → Postgres** and set:

| Field    | Value                            |
| -------- | -------------------------------- |
| Host     | `db`  (service name on the compose network) |
| Database | `sentinel`                       |
| User     | `sentinel`                       |
| Password | `sentinel`                       |
| Port     | `5432`                           |

n8n runs in the same compose network as `db`, so use the host `db`, **not**
`localhost`.

Or import the ready-made credential from the CLI (id `sentinel-postgres`):

```bash
docker cp n8n/credentials.local.json sentinel-n8n:/tmp/credentials.json
docker exec sentinel-n8n n8n import:credentials --input=/tmp/credentials.json
```

## 3. Import + activate the workflow

**Workflows → Import from File →** `n8n/workflows/webhook-to-tickets.json`, then
open the **Insert ticket** node and confirm the **Sentinel Postgres** credential
is selected. Save and flip **Active** to ON.

> Activation must happen through the running instance (the UI toggle). Marking a
> workflow active purely via `n8n import:workflow` does not always register the
> production webhook until the instance re-activates it.

## 4. Test

```bash
curl -X POST http://localhost:5679/webhook/ticket \
  -H "Content-Type: application/json" \
  -d '{"subject":"Cannot log in","body":"500 on /login","requester_email":"a@b.com","route":"escalate","urgency":"high","reason":"router_escalate"}'
```

Expected response: `{"ok":true,"id":"1"}`. The editor's test URL
`/webhook-test/ticket` works the same way once the workflow is active.

Verify:

```bash
docker compose exec -T db psql -U sentinel -d sentinel -c "SELECT id, subject, route FROM tickets ORDER BY id DESC LIMIT 5;"
```

Only `subject` is required; every other field is optional and defaults are
applied by the table (`body=''`, `status='open'`, `created_at=now()`).
