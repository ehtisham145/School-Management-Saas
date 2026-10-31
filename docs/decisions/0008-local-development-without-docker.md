# ADR-0008: Local development without mandatory Docker; Python 3.11; pip

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Development happens on two machines: an office laptop with 8 GB RAM, where Docker Desktop would make the system unusably slow, and a home desktop with 16 GB RAM, which can run Docker Desktop. Python 3.11 is already installed, and the developer prefers plain pip.

## Decision
- Docker is **required only on servers** (staging/production) and in CI image builds.
- Laptop: native PostgreSQL 17, no Redis. Settings fall back to in-memory cache, eager Celery and `InMemoryChannelLayer` when `REDIS_URL` is unset.
- Desktop: Docker Desktop runs Postgres + Redis via `infra/docker-compose.dev.yaml`; the app itself runs natively.
- **Python 3.11** everywhere, including the production Docker image (`python:3.11-slim`), so local and server match. Django 5.2 LTS supports it; Python 3.11 receives security fixes until Oct 2027 — plan an upgrade before then.
- **pip + venv** with pinned `requirements/{base,dev,prod}.txt`.

Supersedes the "Python 3.13" note in the original [tech-stack.md](../tech-stack.md).

## Consequences
- ✅ Laptop stays fast; no Docker needed to start working.
- ✅ Same Python version locally and in production.
- ⚠️ The laptop doesn't exercise Redis, real Celery workers or multi-process WebSockets → verify those on the desktop or staging before merge.
- ⚠️ Two dev setups to keep working → both documented in [development.md](../development.md).
