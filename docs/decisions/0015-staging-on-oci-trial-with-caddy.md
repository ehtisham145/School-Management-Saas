# ADR-0015: Staging on an OCI trial VM with its own Caddy

- **Status:** Accepted
- **Date:** 2026-11-09
- **Supersedes:** [ADR-0011](0011-staging-on-hostinger-behind-shared-nginx.md)

## Context
Staging ran on the Hostinger VPS behind E-Numerak's nginx ([ADR-0011](0011-staging-on-hostinger-behind-shared-nginx.md)). That server belongs to the company and Lesson Lab must not keep anything on it, so the stack was removed from it on 2026-11-09.

The owner now has an Oracle Cloud test account (home region India South, Hyderabad) with the 30-day free trial credit. The free A1 shape had no capacity, so the VM is a paid `VM.Standard.E5.Flex` (2 OCPU, 12 GB, x86) running Ubuntu 24.04, paid for by the trial credit until about 2026-12-07. The client's production account (Riyadh) is still not ready.

## Decision
- Staging runs at `staging.lessonlab.me` on this VM, set up the way production will be, so the server work is practised before the real launch. **Test data only**: the VM is outside KSA.
- The stack gets its own reverse proxy: **Caddy** (`lessonlab-proxy` in `staging/docker-compose.yml`, config in `staging/caddy/Caddyfile`). It is the only service that publishes ports (80 and 443), gets and renews the Let's Encrypt certificate itself, and sends `/api/`, `/admin/` and `/static/` to the backend and everything else to the frontend. This is the production plan in [tech-stack.md](../tech-stack.md).
- `CADDY_TLS=internal` gives a self-signed certificate, so CI tests the whole path through Caddy without being reachable from the internet.
- Auto-deploy ([ADR-0013](0013-staging-auto-deploy.md)) works as before; `deploy.sh` reloads Caddy when `staging/caddy/` changes.

## Consequences
- Staging and production now use the same proxy, so TLS and routing are tested before launch.
- Ports 80 and 443 have to be open twice on OCI: in the VCN security list and in the VM's own iptables rules.
- The trial ends around 2026-12-07. After that the VM is stopped and later deleted unless the account is upgraded. Before then, staging moves again (to the client's OCI account or a free A1 VM), and this ADR is updated.
- The VM is x86, like the images CI builds today. The production A1 VM is ARM, so CI must build arm64 images before production ([ADR-0004](0004-hosting-oracle-cloud-saudi.md)).
