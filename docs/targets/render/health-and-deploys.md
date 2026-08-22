# Render health checks and deploy behavior

Official sources: https://render.com/docs/health-checks and https://render.com/docs/deploys  
Verified: 2026-08-22  
Snapshot note: concise paraphrase prepared for an attributed support-agent evaluation.

## Health-check success and failed new deploys `[rnd-03]`

Render web services can use an HTTP GET health-check path. A response counts as healthy when it returns a `2xx` or `3xx` status within five seconds. During a deploy, Render sends checks to the new instance before moving traffic. If the new instances do not all become healthy within 15 minutes, Render cancels the deploy and keeps routing traffic to the existing instances. For an already-running instance, consecutive failures first remove it from routing and can eventually trigger an automatic restart.

## Zero-downtime deploy boundary `[rnd-04]`

Render normally deploys services without downtime unless a persistent disk is attached. A failed build or failed replacement instance does not replace the currently successful instance. The old instance continues serving while the new version starts and proves healthy. Persistent disks disable this normal zero-downtime behavior, so disk-backed services need separate downtime planning.
