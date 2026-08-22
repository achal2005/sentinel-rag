# Render regions

Official source: https://render.com/docs/regions  
Verified: 2026-08-22  
Snapshot note: concise paraphrase prepared for an attributed support-agent evaluation.

## Available regions and region changes `[rnd-08]`

Render documents service and datastore regions in Oregon, Ohio, Virginia, Frankfurt, and Singapore. A region is selected during resource creation; static sites instead use a global CDN. Render does not currently support changing the region of an existing service or database in place. To move, create a new resource in the destination region and migrate the configuration and data. Private networking is regional, so services in different regions cannot communicate through the same private network and need secured public communication instead.
