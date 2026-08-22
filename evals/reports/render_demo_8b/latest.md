# Render public-documentation ticket test

Generated: 2026-08-22T03:39:13.450891+00:00

This is an independent technical demonstration using a small, hand-curated, attributed, paraphrased snapshot of Render's public documentation. It is not produced by or affiliated with Render.

## Result

- Tickets: **5**
- Passed: **5**
- Failed: **0**
- Pass rate: **100%**

| Ticket | Result | Route | Expected source cited | Citations retrieved | Citations allowed | Duration |
|---|---|---|---:|---:|---:|---:|
| RENDER-001 | PASSED | answer | yes | yes | yes | 98.1s |
| RENDER-002 | PASSED | answer | yes | yes | yes | 55.7s |
| RENDER-003 | PASSED | answer | yes | yes | yes | 55.1s |
| RENDER-004 | PASSED | answer | yes | yes | yes | 55.8s |
| RENDER-005 | PASSED | answer | yes | yes | yes | 52.8s |

## Ticket evidence

### RENDER-001 — PASSED

**Ticket:** My custom domain verification keeps failing and the DNS zone still has an AAAA record. What should I change, and what happens after verification?

**Official documentation:** https://render.com/docs/custom-domains

**Expected:** Remove the AAAA record, confirm the required DNS records, wait for propagation, and retry verification; managed TLS follows verification.

**Retrieved:** rnd-01, rnd-02, rnd-03, rnd-07

**Cited:** rnd-01, rnd-02

**Failed checks:** none

**Sentinel response:**

Remove the AAAA record from the DNS zone [rnd-01]. After successful verification, Render issues and renews a managed TLS certificate and redirects HTTP traffic to HTTPS [rnd-02]. A newly verified domain can briefly return a 502 while routing rules finish updating; wait a few minutes and retry [rnd-02].
Sources: [rnd-01], [rnd-02]

### RENDER-002 — PASSED

**Ticket:** Our new web-service deploy is failing its HTTP health check. What response counts as healthy, and will Render replace the currently working version?

**Official documentation:** https://render.com/docs/health-checks

**Expected:** A 2xx or 3xx response within five seconds is healthy. A replacement that never becomes healthy is cancelled while the existing instance keeps traffic.

**Retrieved:** rnd-03, rnd-04, rnd-02, rnd-01

**Cited:** rnd-03, rnd-04

**Failed checks:** none

**Sentinel response:**

A response counts as healthy when it returns a `2xx` or `3xx` status within five seconds [rnd-03]. Render will not replace the currently working version [rnd-04].

Sources: [rnd-03], [rnd-04]

### RENDER-003 — PASSED

**Ticket:** I changed an environment variable and want the running service to pick it up without rebuilding the code. Which save option should I use?

**Official documentation:** https://render.com/docs/configure-environment-variables

**Expected:** Use Save and deploy, which redeploys the existing build with the new environment values instead of creating a new build.

**Retrieved:** rnd-05, rnd-03, rnd-08, rnd-07

**Cited:** rnd-05

**Failed checks:** none

**Sentinel response:**

To pick up the changed environment variable without rebuilding the code, you should use **Save and deploy** [rnd-05]. This option redeploys the existing build with the new values, avoiding a rebuild.

Sources: [rnd-05]

### RENDER-004 — PASSED

**Ticket:** Can a Hobby workspace restore a paid Render Postgres database to five days ago? Would upgrading to Pro today make that older restore available?

**Official documentation:** https://render.com/docs/postgresql-backups

**Expected:** No. Hobby has a three-day PITR window, and an upgrade to Pro extends the window only going forward rather than backfilling older history.

**Retrieved:** rnd-06, rnd-07

**Cited:** rnd-06

**Failed checks:** none

**Sentinel response:**

A Hobby workspace can restore a paid Render Postgres database to the past three days [rnd-06]. Upgrading to Pro today would extend the recovery window to seven days, but it would not make the older restore available [rnd-06].
Sources: [rnd-06]

### RENDER-005 — PASSED

**Ticket:** We need to move an existing Render service from Oregon to Frankfurt. Can its region be changed in place, or what migration path do the docs require?

**Official documentation:** https://render.com/docs/regions

**Expected:** Render does not support an in-place region change. Create a new resource in Frankfurt and migrate configuration and data.

**Retrieved:** rnd-08, rnd-05, rnd-03

**Cited:** rnd-08

**Failed checks:** none

**Sentinel response:**

To move an existing Render service from Oregon to Frankfurt, you cannot change the region in place [rnd-08]. Instead, you need to create a new resource in the destination region and migrate the configuration and data [rnd-08]. Private networking is regional, so services in different regions cannot communicate through the same private network and need secured public communication instead [rnd-08].

Sources: [rnd-08]

## Limitations

- The corpus is a hand-curated, attributed, paraphrased snapshot, not Render's complete documentation.
- Deterministic checks validate routing, retrieval, citation-ID membership, and required or forbidden phrases; they do not prove semantic entailment or human support quality.
- No Render account, private data, or production API was accessed.
