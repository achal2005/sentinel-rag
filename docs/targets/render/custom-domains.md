# Render custom domains

Official source: https://render.com/docs/custom-domains  
Verified: 2026-08-22  
Snapshot note: concise paraphrase prepared for an attributed support-agent evaluation.

## Configure and verify a custom domain `[rnd-01]`

Custom domains are supported for Render web services and static sites. Setup has three parts: add the domain from the service's Settings page, configure the required DNS records at the DNS provider, and return to the dashboard to verify it. During setup, remove `AAAA` records because Render directs custom-domain traffic over IPv4 and an IPv6 record can interfere with verification or routing. DNS propagation can take time, so a failed verification should be retried after waiting a few minutes.

## TLS and post-verification behavior `[rnd-02]`

After successful verification, Render issues and renews a managed TLS certificate and redirects HTTP traffic to HTTPS. A newly verified domain can briefly return a 502 while routing rules finish updating; the documentation recommends waiting a few minutes and retrying. If the domain defines CAA records, they must permit Render's certificate authorities. A service keeps its `onrender.com` subdomain unless that subdomain is explicitly disabled.
