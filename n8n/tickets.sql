-- Schema for the 'tickets' table written by the n8n webhook workflow.
-- Run against the same Postgres the app uses:
--   docker compose exec -T db psql -U sentinel -d sentinel < n8n/tickets.sql

CREATE TABLE IF NOT EXISTS tickets (
    id              BIGSERIAL PRIMARY KEY,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    requester_email TEXT,
    route           TEXT,                 -- answer | action | escalate | spam (from the router)
    urgency         TEXT,                 -- low | normal | high (optional)
    reason          TEXT,                 -- short machine tag for tracing
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tickets_status_idx  ON tickets (status);
CREATE INDEX IF NOT EXISTS tickets_created_idx ON tickets (created_at DESC);
