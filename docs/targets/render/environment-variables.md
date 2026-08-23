# Render environment variables and secrets

Official source: https://render.com/docs/configure-environment-variables  
Verified: 2026-08-22  
Snapshot note: concise paraphrase prepared for an attributed support-agent evaluation.

## Choose how an environment-variable change is applied `[rnd-05]`

Environment variables are edited from a service's Environment page. When saving a change, the dashboard offers three behaviors. **Save, rebuild, and deploy** creates a new build and deploys it with the new values. **Save and deploy** redeploys the existing build with the new values, avoiding a rebuild. **Save only** stores the values without deploying, so the running service will not use them until a later deploy. Render also supports bulk `.env` input, environment groups, and secret files; secret values should not be committed to source control or placed directly in a Blueprint.
