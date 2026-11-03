# CLAUDE.md

Multi-tenant School Management SaaS for private schools in Saudi Arabia.
Django 5.2 + DRF (Python 3.11) backend, Next.js + TypeScript frontend, PostgreSQL 17, Celery, Channels.

## Read first
- [docs/README.md](docs/README.md) — index and core rules
- [docs/architecture.md](docs/architecture.md) — tenancy, auth, RBAC, folder structure
- [docs/security.md](docs/security.md) — non-negotiable security rules
- [docs/development.md](docs/development.md) — local setup, git workflow, definition of done
- [docs/roadmap.md](docs/roadmap.md) — what we are building now

## Non-negotiable rules
1. Every tenant-owned model inherits `TenantModel`. Every read goes through a selector that takes `school` first. Never use `Model.objects` on a tenant model in views.
2. `request.school` comes only from the session membership — never from URL, header or body.
3. Views are thin. Writes go in `services.py`, reads in `selectors.py`. Never import another app's models in views — use its services/selectors.
4. Every endpoint ships with a cross-tenant test (other school → 404) and role permission tests.
5. No hard-coded UI text (use `messages/ar.json`, `messages/en.json`). Use logical CSS only (`ms-`, `pe-`, `start-`, `end-`), never `left`/`right`.
6. Dates stored Gregorian/UTC; Hijri is display only.
7. Vendors (email, payments, AI) only through `apps/integrations/` adapters.
8. Money is `Decimal`, never float. No secrets in git.

## Design
The approved look is in `design/` (read `design/PROMPT.md`). Colors, radius and fonts come only from the tokens in `frontend/src/app/globals.css`. Don't add a second visual style.

## Local environment
- Two machines: laptop without Docker (native Postgres, no Redis), desktop with Docker Desktop (Postgres + Redis).
- Never assume Redis exists locally: settings fall back to in-memory when `REDIS_URL` is unset.
- Python 3.11 + venv + pip (`backend/requirements/*.txt`). Node 24 + npm.

## Workflow
- Never commit to `main`. Branch per task: `feature/…`, `fix/…`, `docs/…`, `chore/…`.
- Conventional Commits: `feat(attendance): …`, `fix(auth): …`.
- Small, focused changes. Propose a plan before large changes.
- Run `ruff`, `pytest`, `eslint`, `tsc` before saying work is done.

## Keep docs in sync
Whenever a change affects any of the following, update the matching doc **in the same branch/PR**:

| Change | Update |
|---|---|
| New module, model or relationship | `docs/architecture.md` (data model, folder structure) |
| New/changed technology or library choice | `docs/tech-stack.md` + a new ADR in `docs/decisions/` |
| Significant decision or reversal | New ADR (`NNNN-short-title.md`); mark the old one "Superseded by ADR-NNNN" |
| Auth, permissions, data handling | `docs/security.md` |
| Setup, commands, env vars | `docs/development.md` + `.env.example` |
| Task finished or scope moved | Tick/move items in `docs/roadmap.md` |
| Requirement clarified by the client | `docs/requirements.md` (remove the TBC) |

Small changes (bug fixes, styling, refactors with no behaviour change) don't need doc updates. When unsure, mention it to the user instead of skipping silently.

## Talking to the user
The user prefers **Roman Urdu, short and simple answers**. Code, docs, comments and commit messages stay in English.
