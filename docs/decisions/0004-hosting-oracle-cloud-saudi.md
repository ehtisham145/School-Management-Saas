# ADR-0004: Host on Oracle Cloud Riyadh, single VM with Docker Compose

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Data must stay in Saudi Arabia (client requirement, latency, PDPL). Budget ~$20/month. The developer is comfortable managing VPSs and Docker.

Facts as of Oct 2026:
- Oracle Cloud has two Saudi regions: Jeddah (`me-jeddah-1`) and Riyadh (`me-riyadh-1`).
- OCI Always Free Ampere A1 was cut in mid-2026 to 1,500 OCPU-hours / 9,000 GB-hours per month (≈ 2 OCPU / 12 GB continuously). Always Free compute is only in the home region, and A1 capacity is often limited.
- AWS Saudi region is scheduled for December 2026; local Saudi VPS providers charge roughly $30–60/month for 2 vCPU / 4 GB.

## Decision
- OCI account with **home region Riyadh** (fallback Jeddah if A1 capacity is unavailable), upgraded to **Pay-As-You-Go** (free allowances remain; avoids idle reclamation; paid capacity available instantly).
- One Ampere A1 VM (2 OCPU / 12 GB, Ubuntu 24.04) running Docker Compose: Caddy, Next.js, Django ASGI, Celery worker, Celery beat, PostgreSQL, Redis.
- OCI Object Storage (S3-compatible) for files; nightly encrypted DB backups to the **other** Saudi region.
- Images built multi-arch (arm64) in GitHub Actions.

## Consequences
- ✅ ~$0–5/month at launch, data in KSA, cross-region backups inside KSA.
- ⚠️ Single point of failure → off-VM backups, scripted rebuild (<1 hour), documented restore.
- ⚠️ Free capacity not guaranteed → set a budget alert in OCI; be ready to pay for a small paid shape.
- ⚠️ Vendor-specific bits kept minimal (S3 API, plain VMs) so moving to AWS KSA or a local provider is a redeploy, not a rewrite.

## Revisit when
~10 schools (move DB to its own server/managed service) or if the client prefers AWS once its Saudi region is live.
