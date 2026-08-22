# Render public-documentation ticket test

Generated: 2026-08-22T03:39:16.850963+00:00

This is an independent technical demonstration using a small, hand-curated, attributed, paraphrased snapshot of Render's public documentation. It is not produced by or affiliated with Render.

## Result

- Tickets: **5**
- Passed: **2**
- Failed: **3**
- Pass rate: **40%**

| Ticket | Result | Route | Expected source cited | Citations retrieved | Citations allowed | Duration |
|---|---|---|---:|---:|---:|---:|
| RENDER-001 | PASSED | answer | yes | yes | yes | 11.5s |
| RENDER-002 | PASSED | answer | yes | yes | yes | 10.7s |
| RENDER-003 | FAILED | answer | yes | yes | no | 10.0s |
| RENDER-004 | FAILED | answer | yes | yes | no | 9.7s |
| RENDER-005 | FAILED | answer | yes | yes | no | 6.9s |

## Ticket evidence

### RENDER-001 — PASSED

**Ticket:** My custom domain verification keeps failing and the DNS zone still has an AAAA record. What should I change, and what happens after verification?

**Official documentation:** https://render.com/docs/custom-domains

**Expected:** Remove the AAAA record, confirm the required DNS records, wait for propagation, and retry verification; managed TLS follows verification.

**Retrieved:** rnd-01, rnd-02, rnd-03, rnd-07

**Cited:** rnd-01, rnd-02

**Failed checks:** none

**Sentinel response:**

To resolve the issue with your custom domain verification failing due to an existing AAAA record, you should remove the AAAA record from your DNS zone.

After successful verification, Render will issue and renew a managed TLS certificate and redirect HTTP traffic to HTTPS.

Sources: [rnd-01], [rnd-02]

### RENDER-002 — PASSED

**Ticket:** Our new web-service deploy is failing its HTTP health check. What response counts as healthy, and will Render replace the currently working version?

**Official documentation:** https://render.com/docs/health-checks

**Expected:** A 2xx or 3xx response within five seconds is healthy. A replacement that never becomes healthy is cancelled while the existing instance keeps traffic.

**Retrieved:** rnd-03, rnd-04, rnd-02, rnd-01

**Cited:** rnd-03, rnd-04

**Failed checks:** none

**Sentinel response:**

To pass the HTTP health check, a response must return a `2xx` or `3xx` status within five seconds [rnd-03]. Render will not replace the currently working version if the new instance does not become healthy within 15 minutes [rnd-03]. 

Sources: [rnd-03], [rnd-04]

### RENDER-003 — FAILED

**Ticket:** I changed an environment variable and want the running service to pick it up without rebuilding the code. Which save option should I use?

**Official documentation:** https://render.com/docs/configure-environment-variables

**Expected:** Use Save and deploy, which redeploys the existing build with the new environment values instead of creating a new build.

**Retrieved:** rnd-05, rnd-03, rnd-08, rnd-07

**Cited:** rnd-05, rnd-03

**Failed checks:** citations_relevant

**Sentinel response:**

To make the running service pick up the environment variable change without rebuilding the code, you should use the **Save and deploy** option.

Sources: [rnd-05], [rnd-03]

### RENDER-004 — FAILED

**Ticket:** Can a Hobby workspace restore a paid Render Postgres database to five days ago? Would upgrading to Pro today make that older restore available?

**Official documentation:** https://render.com/docs/postgresql-backups

**Expected:** No. Hobby has a three-day PITR window, and an upgrade to Pro extends the window only going forward rather than backfilling older history.

**Retrieved:** rnd-06, rnd-07

**Cited:** rnd-06, rnd-07

**Failed checks:** required_concepts_present, citations_relevant

**Sentinel response:**

A Hobby workspace can restore a paid Render Postgres database to five days ago, but only if the database was upgraded to Pro before the five-day mark [rnd-06]. Upgrading to Pro today would not make the older restore available [rnd-06].
Sources: [rnd-06], [rnd-07]

### RENDER-005 — FAILED

**Ticket:** We need to move an existing Render service from Oregon to Frankfurt. Can its region be changed in place, or what migration path do the docs require?

**Official documentation:** https://render.com/docs/regions

**Expected:** Render does not support an in-place region change. Create a new resource in Frankfurt and migrate configuration and data.

**Retrieved:** rnd-08, rnd-05, rnd-03

**Cited:** rnd-08, rnd-05, rnd-03

**Failed checks:** citations_relevant

**Sentinel response:**

To move an existing Render service from Oregon to Frankfurt, Render does not currently support changing the region of an existing service or database in place. Instead, create a new resource in the destination region and migrate the configuration and data.

Sources: [rnd-08], [rnd-05], [rnd-03]

## Limitations

- The corpus is a hand-curated, attributed, paraphrased snapshot, not Render's complete documentation.
- Deterministic checks validate routing, retrieval, citation-ID membership, and required or forbidden phrases; they do not prove semantic entailment or human support quality.
- No Render account, private data, or production API was accessed.
