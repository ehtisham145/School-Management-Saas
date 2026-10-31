# Development Guide

## 1. Local environments

Two machines, one codebase. The only difference is the `.env` file.

| | Office laptop (8 GB RAM) | Home desktop (16 GB RAM) |
|---|---|---|
| Docker | No | Docker Desktop |
| Python | 3.11 + `venv` + `pip` | 3.11 + `venv` + `pip` |
| PostgreSQL 17 | Installed natively on Windows | Container from `infra/docker-compose.dev.yaml` |
| Redis | Not used | Container from `infra/docker-compose.dev.yaml` |
| Node.js | 24 (npm) | 24 (npm) |

Django, Celery and Next.js run **natively on both machines** (not in Docker), so hot reload stays fast. Docker on the desktop only runs the services.

### Redis-optional settings
`config/settings/base.py` checks `REDIS_URL`:

| | `REDIS_URL` set (desktop, servers) | `REDIS_URL` unset (laptop) |
|---|---|---|
| Cache | Redis | `LocMemCache` |
| Celery | Real broker; run a worker | `CELERY_TASK_ALWAYS_EAGER=True` (tasks run inline) |
| Channels layer | `channels_redis` | `InMemoryChannelLayer` |
| Sessions | Redis-backed cache + DB | DB |

**Rule:** code must never assume Redis exists in dev. Anything that only works with Redis (e.g. multi-process WebSocket fan-out) is verified on the desktop or on staging before merge.

Production is always Redis + Docker. Laptop-only testing is not enough for changes to background jobs or real-time features; check them on staging.

### First-time setup

Prerequisites: Git, Python 3.11, Node 24. Laptop: PostgreSQL 17 installed natively. Desktop: Docker Desktop (WSL 2).

**1. Clone**
```
git clone https://github.com/ehtisham145/school-management-saas.git
cd school-management-saas
```

**2. Database**

Laptop — create the user and database once with psql:
```
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres
```
```sql
CREATE USER school_saas WITH PASSWORD 'devpass123';
CREATE DATABASE school_saas OWNER school_saas;
ALTER USER school_saas CREATEDB;   -- pytest creates a test database
\q
```

Desktop — start Postgres + Redis containers (same user/password/db as above):
```
docker compose -f infra/docker-compose.dev.yaml up -d
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
REDIS_URL=redis://localhost:6379/0   # desktop only — leave out on the laptop
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

**5. Git hooks** (from the repo root, with the backend venv active)
```
pre-commit install
pre-commit run --all-files          # first run may "fail" after auto-fixing files; run it again
```

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
- Keep PRs small: one feature or one fix.
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

## 7. Definition of done
- [ ] Code + tests written, CI green
- [ ] Checked in Arabic (RTL) and English
- [ ] Cross-tenant test proves another school can't see the data
- [ ] Significant decision recorded as an ADR
