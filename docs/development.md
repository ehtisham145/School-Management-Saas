# Development Guide

## 1. Local environments

Two machines, one codebase, **one setup**: both run native PostgreSQL 17, no Redis. ([ADR-0009](decisions/0009-local-development-fully-native.md), which superseded the earlier laptop/desktop split in [ADR-0008](decisions/0008-local-development-without-docker.md).)

| | Office laptop (8 GB RAM) | Home desktop (16 GB RAM) |
|---|---|---|
| Docker | No | No (Docker Desktop available but not used for local dev) |
| Python | 3.11 + `venv` + `pip` | 3.11 + `venv` + `pip` |
| PostgreSQL 17 | Installed natively on Windows | Installed natively on Windows |
| Redis | Not used | Not used |
| Node.js | 24 (npm) | 24 (npm) |

Django, Celery and Next.js run **natively on both machines**, so hot reload stays fast.

### Redis-optional settings
`config/settings/base.py` checks `REDIS_URL`:

| | `REDIS_URL` set (servers) | `REDIS_URL` unset (both local machines) |
|---|---|---|
| Cache | Redis | `LocMemCache` |
| Celery | Real broker; run a worker | `CELERY_TASK_ALWAYS_EAGER=True` (tasks run inline) |
| Channels layer | `channels_redis` | `InMemoryChannelLayer` |
| Sessions | Redis-backed cache + DB | DB |

**Rule:** code must never assume Redis exists in dev. Anything that only works with Redis (e.g. multi-process WebSocket fan-out, real Celery concurrency) is verified **on staging** before merge — neither local machine exercises it.

Production is always Redis + Docker.

### First-time setup

Prerequisites: Git, Python 3.11, Node 24, PostgreSQL 17 installed natively.

**1. Clone**
```
git clone https://github.com/ehtisham145/school-management-saas.git
cd school-management-saas
```

**2. Database**

Create the user and database once with psql (same on both machines):
```
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres
```
```sql
CREATE USER school_saas WITH PASSWORD 'devpass123';
CREATE DATABASE school_saas OWNER school_saas;
ALTER USER school_saas CREATEDB;   -- pytest creates a test database
\q
```

**3. Backend** (PowerShell)
```
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements/dev.txt
copy .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Fill `.env`:
```
SECRET_KEY='<generated key, in single quotes>'
DATABASE_URL=postgres://school_saas:devpass123@localhost:5432/school_saas
# REDIS_URL left unset on both machines
```
Special characters in the DB password must be URL-encoded in `DATABASE_URL` (`@` → `%40`, `#` → `%23`).
```
python manage.py migrate
pytest
python manage.py runserver          # http://127.0.0.1:8000
```

**4. Frontend**
```
cd ../frontend
npm install
npm run dev                         # http://localhost:3000 → /en or /ar
```
`next.config.ts` rewrites `/api/*` to the Django backend so the browser and
API share an origin locally (same as production, where Caddy does this
instead). It defaults to `http://127.0.0.1:8000`; copy `.env.example` to
`.env.local` only if your backend runs somewhere else.

**5. Git hooks** (from the repo root, with the backend venv active)
```
pre-commit install
pre-commit run --all-files          # first run may "fail" after auto-fixing files; run it again
```

To use the Super Admin panel at `/platform`, tick **Is platform admin** on your user in Django admin (`createsuperuser` does not set it). The first website login asks you to set up 2FA.

`LEADS_EMAIL` sets who receives Book a demo and Contact form emails (default `info@lessonlab.me`). Without `EMAIL_HOST` in `.env`, emails are printed in the Django terminal. With it, they go through SMTP (see `.env.example`). Check the settings with `python manage.py sendtestemail you@example.com`. Port 587 uses `EMAIL_USE_TLS=True`; port 465 uses `EMAIL_USE_TLS=False` and `EMAIL_USE_SSL=True`.

If the frontend build complains about pages that no longer exist, or the dev server shows old styles after CSS changes, stop it, delete the generated `frontend/.next` folder and start it again.

### Everyday commands

| Where | Command | Purpose |
|---|---|---|
| backend | `ruff check . --fix` | Lint + auto-fix |
| backend | `ruff format .` | Format |
| backend | `pytest` | Tests |
| frontend | `npm run lint` | ESLint |
| frontend | `npm run format` / `npm run format:check` | Prettier write / check |
| frontend | `npx tsc --noEmit` | Type check |
| frontend | `npm run build` | Production build (catches errors `dev` hides) |
| root | `pre-commit run --all-files` | All hooks on every file |

Switching machines: always `git pull` before starting work, and commit + push before leaving.

## 2. Git workflow
- `main` is always deployable. No direct commits to `main`.
- One branch per task: `feature/attendance`, `fix/login-otp`, `docs/...`, `chore/...`.
- Open a PR, CI must be green, run an AI review, then merge. Delete the branch after merging.
- Scope a PR to one complete, working module — not a tiny fragment (e.g. "add a model" alone), and not a sprawling grab-bag either. When two pieces share real infrastructure (e.g. TOTP 2FA and email OTP both need the same Celery/email setup), build them together in one PR rather than splitting purely for size. The bar: after merge, that one thing works end-to-end.
- Merging to `main` deploys automatically (once CI/CD is set up).

## 3. Commit messages (Conventional Commits)
```
feat(attendance): add daily attendance marking
fix(auth): block OTP after 5 wrong attempts
refactor(fees): move receipt logic to services
docs: update roadmap
chore: bump dependencies
test(exams): add cross-tenant tests for marks API
```

## 4. Code quality tools
| Tool | Checks |
|---|---|
| `ruff` | Python lint + format |
| `eslint` + `prettier` | TypeScript/React lint + format |
| `tsc --noEmit` | TypeScript type errors (strict mode) |
| `pytest` | Backend tests |
| `pre-commit` | Before each commit: whitespace/EOF fixes, YAML check, large-file and private-key guards, ruff, eslint, prettier (`.pre-commit-config.yaml`) |

CI runs all of these on every PR.

## 5. Tests — what is required
- **Cross-tenant test for every endpoint** (mandatory).
- Permission tests per role for sensitive actions (marks, fees, attendance, users).
- Service tests for business logic (fee totals, grade calculation).
- Coverage percentage is not a goal; critical paths are.

## 6. Working with the AI agent
1. Give one small task at a time (one model, one service, one screen).
2. Ask for a plan first, then the code.
3. Read the critical parts yourself: school filtering, permissions, auth/OTP, fees, marks.
4. Ask the agent to explain anything unclear before merging.
5. Tests must pass; run an AI review on the PR.

## 7. Frontend conventions
- Colors, radius and fonts come only from the tokens in `frontend/src/app/globals.css`.
- Forms use `useValidatedForm` and `Field`: `*` on required fields, errors that clear as soon as the value is valid, and scrolling to the first error on submit.
- Text goes in `messages/en.json` and `messages/ar.json`. A key missing from either fails the type check.
- Next.js keeps visited pages alive (`cacheComponents`), so `useState` survives navigation. Reset anything that must start fresh, such as sign-in steps and scroll effects.
- Before saying a screen works, try it in a browser in `npm run dev`, in Arabic and English, at phone and desktop widths.

## 8. Definition of done
- [ ] Code + tests written, CI green
- [ ] Checked in Arabic (RTL) and English
- [ ] Cross-tenant test proves another school can't see the data
- [ ] Significant decision recorded as an ADR
