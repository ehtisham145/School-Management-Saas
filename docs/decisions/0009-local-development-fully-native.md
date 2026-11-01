# ADR-0009: Local development fully native on both machines; Docker only for servers/CI

- **Status:** Accepted
- **Date:** 2026-11-01

## Context
[ADR-0008](0008-local-development-without-docker.md) set up two different local dev modes: laptop native (no Docker, no Redis), desktop with Docker Desktop running Postgres + Redis via `infra/docker-compose.dev.yaml`. In practice, the desktop also now runs PostgreSQL 17 natively (Windows installer, own superuser/db/role), matching the laptop. Keeping Docker Desktop as a second desktop-only path added setup overhead (a buggy, unused `docker-compose.dev.yaml`) without a concrete benefit yet.

## Decision
- Both machines (laptop and desktop) run **native PostgreSQL 17, no Redis**, for local development.
- `REDIS_URL` stays unset on both; settings keep falling back to `LocMemCache`, eager Celery, and `InMemoryChannelLayer` (unchanged from ADR-0008's Redis-optional mechanism — this is now the standing default everywhere locally, not just on the laptop).
- Docker is used **only** for staging/production and CI image builds, as already stated in ADR-0008.
- `infra/docker-compose.dev.yaml` is no longer part of the standard local setup. It is not deleted outright (still useful as a quick reference or if Docker Desktop is reinstalled later), but it is **not maintained** going forward — don't assume it works without checking it first.
- Redis-dependent behavior (real Celery workers, multi-process Channels fan-out) is verified **only on staging**, not on either local machine.

## Consequences
- ✅ One setup story instead of two; simpler onboarding, nothing Docker-related required to start coding locally.
- ✅ Still matches ADR-0008's core idea: same Python version and settings code path everywhere, Redis truly optional.
- ⚠️ Neither local machine exercises Redis, real Celery, or multi-process WebSockets — every change touching those **must** be verified on staging before merge, not just "it works with REDIS_URL unset."
- ⚠️ If `infra/docker-compose.dev.yaml` is picked back up later, re-check it (it had a typo in `environment:` and a misplaced `redis:` service nested under `postgres:` as of 2026-11-01) before trusting it.
