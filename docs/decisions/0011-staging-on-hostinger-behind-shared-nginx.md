# ADR-0011: Staging on Hostinger behind the shared nginx

- **Status:** Superseded by [ADR-0015](0015-staging-on-oci-trial-with-caddy.md)
- **Date:** 2026-11-05

## Context
Redis, Celery and the Docker images can only be verified on a real server ([ADR-0009](0009-local-development-fully-native.md)), and the client's OCI hosting isn't ready. The owner already has a Hostinger VPS in France that runs the E-Numerak staging site. That site's nginx container owns ports 80 and 443.

## Decision
- Staging runs at `staging.lessonlab.me` on the Hostinger VPS, with **test data only**. It must never hold real school data, because the server is outside KSA.
- The stack lives in `staging/` as its own Compose project, with its own PostgreSQL and Redis. It shares nothing with E-Numerak except nginx.
- It publishes no ports. nginx joins the `lessonlab-edge` Docker network and reaches `lessonlab-backend:8000` and `lessonlab-frontend:3000`.
- Service names start with `lessonlab-`, so a name on the shared network can't also answer for an E-Numerak service.
- Caddy stays the plan for production on OCI. It isn't used here because nginx already owns the ports.

## Consequences
- nginx is the only part of staging that differs from the production plan, so TLS and proxy behaviour must be checked again on OCI.
- A change to the nginx config can affect E-Numerak, so test it with `nginx -t` and keep a backup before reloading.
- Both sites share 2 CPUs and 7.8 GB of RAM, so every Lesson Lab service has CPU, memory and process limits.
