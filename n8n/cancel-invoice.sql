-- Schema for the 'invoice_cancellations' table written by the n8n
-- 'Webhook -> cancel_invoice' workflow when a high-risk cancellation is approved.
--   docker compose exec -T db psql -U sentinel -d sentinel < n8n/cancel-invoice.sql
-- (The app also creates this table via backend/app/db.py's schema.)

CREATE TABLE IF NOT EXISTS invoice_cancellations (
    id              BIGSERIAL PRIMARY KEY,
    invoice_id      TEXT NOT NULL,
    requester_email TEXT,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'cancelled',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS invcancel_created_idx ON invoice_cancellations (created_at DESC);
