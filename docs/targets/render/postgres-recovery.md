# Render Postgres recovery

Official source: https://render.com/docs/postgresql-backups  
Verified: 2026-08-22  
Snapshot note: concise paraphrase prepared for an attributed support-agent evaluation.

## Point-in-time recovery windows `[rnd-06]`

Paid Render Postgres databases receive point-in-time recovery. The documented recovery window is the past three days for a Hobby workspace and the past seven days for Pro or higher. Upgrading does not create historical recovery coverage retroactively; the longer window grows only from the upgrade forward. A recovery creates a separate database instance at the selected time so it can be validated before applications are pointed to it. Free database instances do not receive managed recovery or backup capabilities.

## Logical backup boundary `[rnd-07]`

Logical backups can be created and downloaded from the database Recovery page for supported paid instances. Render retains a created logical backup for seven days. For recent data-loss incidents, the documentation recommends point-in-time recovery because it can usually restore a more recent state than the latest logical export.
