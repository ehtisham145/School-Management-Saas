# Session Prompts

Copy-paste prompts for starting a fresh Claude Code session each day.
Paste **Part A + the day's Part B** together as the first message.

---

## Part A — Session starter (paste every time)

```
Project: multi-tenant School Management SaaS for Saudi Arabia.
Read CLAUDE.md, docs/README.md, docs/architecture.md, docs/security.md, docs/development.md
and docs/roadmap.md before guiding me. Then run `git status`, `git log --oneline -5` and
`git branch -a` and tell me where we are.

HOW WE WORK:
- I type all code and run all commands MYSELF so I learn. Do NOT edit project files unless I
  explicitly ask (you may offer to do docs-only updates).
- Guide ONE step at a time: the command or code to paste + a short "why" (small table ok).
  Then wait for my output.
- After each step, verify my files with read-only commands and point out mistakes.
- When I paste an error, find the root cause and explain it simply.
- Talk to me in Roman Urdu, short and simple. Code, docs and commit messages in English
  (Conventional Commits).
- Next.js is 16.4 (very new; middleware is src/proxy.ts). Read frontend/node_modules/next/dist/docs
  and current library docs before giving Next.js / shadcn / next-intl code. Don't rely on memory.
- One branch + one PR per day. Before the PR: ruff check, ruff format, pytest, npm run lint,
  npm run build, and update docs per the "Keep docs in sync" table in CLAUDE.md.

MACHINE: <laptop: no Docker, native Postgres, no Redis>  OR  <desktop: Docker Desktop, Postgres +
Redis via infra/docker-compose.dev.yaml, REDIS_URL set in backend/.env>
```

---

## Part B — Day prompts

### Day 2 — Multi-tenancy
```
TODAY: Day 2 — multi-tenancy. Branch: feature/multi-tenancy. This is the most important day; go slowly
and explain each concept before code.

Steps:
1. Reset the local DB (drop + recreate school_saas; nothing important in it yet).
2. apps/accounts: custom User model (AUTH_USER_MODEL) BEFORE any real migration. Email login for staff/
   parents, optional unique username for students, is_platform_admin flag for Super Admin,
   preferred_language (ar/en).
3. apps/core: abstract TenantModel (school FK indexed, created_at, updated_at).
4. apps/tenancy: School (name_ar, name_en, code, is_active), Membership(user, school, role:
   SCHOOL_ADMIN|PRINCIPAL|TEACHER|STUDENT|PARENT, status). Unique (user, school, role).
5. TenantMiddleware: sets request.school and request.role from the session's active membership ONLY
   (never from URL/header/body).
6. apps/core: TenantScopedViewSet base — queryset always filtered by request.school; other school -> 404.
7. Register models in Django admin (temporary Super Admin UI).
8. pytest fixtures with TWO schools + users; first cross-tenant test.
9. Update docs/architecture.md (data model) and docs/roadmap.md, then PR.

Design reference: docs/architecture.md sections 2, 4, 5 and ADR-0002, ADR-0003.
Done when: migrations clean, pytest green, a user of School B gets 404 on School A data.
```

### Day 3 — Authentication
```
TODAY: Day 3 — authentication. Branch: feature/auth. Day 2 (multi-tenancy) is merged.

Steps:
1. Session auth APIs (DRF): login (email+password), logout, me (user + memberships + active school).
2. Student login with username + password (username globally unique, school-prefixed e.g. alnoor.s1024).
3. Parent email OTP: request + verify. 6 digits, stored hashed, 10-min expiry, single use, max 5
   attempts, resend throttled. Email via django-anymail behind apps/integrations/email (console
   backend locally).
4. TOTP 2FA with django-otp: setup (QR), verify, recovery codes. Mandatory for platform admin and
   SCHOOL_ADMIN.
5. Switch-school endpoint (validates membership server-side, rotates session).
6. django-axes lockout + DRF throttling on auth/OTP endpoints. Same error for unknown user and wrong
   password.
7. Session/CSRF settings per docs/security.md section 2.
8. Tests for every login method, wrong password/OTP, lockout, 2FA required, switch-school to a school
   I don't belong to -> rejected.
9. Update docs/security.md (tick items), docs/development.md (.env changes), roadmap, then PR.

Design reference: ADR-0003, docs/architecture.md section 3, docs/security.md sections 2-3.
```

### Day 4 — Roles, Super Admin, frontend login
```
TODAY: Day 4 — RBAC, Super Admin, frontend login. Branch: feature/rbac-and-login. Day 3 is merged.

Backend:
1. apps/core/policies.py: permission matrix can(role, action), default deny; DRF permission class
   using it.
2. Row scoping helpers in selectors (teacher -> assigned sections later; parent -> own children later).
   For now: role-based access on School/Membership endpoints.
3. Platform (Super Admin) endpoints under /api/platform/: create school + its SCHOOL_ADMIN, list
   schools. Audit-log these actions.
4. drf-spectacular: /api/schema/ and /api/docs/ (dev only).

Frontend:
5. Generate a typed API client from the OpenAPI schema (pick a maintained tool; check current docs).
   Fetch wrapper sends credentials + X-CSRFToken.
6. Dev proxy so frontend and API share an origin locally (Next.js rewrites /api -> Django).
7. Pages under app/[locale]/(auth): login (email/password), student login (username), parent email
   OTP, 2FA step. All text from messages/ar.json + en.json; logical CSS only.
8. After login: app/[locale]/(app)/dashboard showing name, role and a school switcher.
9. Check every page in /ar (RTL) and /en.
10. Tests (backend policies + platform endpoints), docs, PR.
```

### Day 5 — Staging server + CI/CD
```
TODAY: Day 5 — staging live. Branch: chore/deploy. Days 2-4 merged.

Steps:
1. Oracle Cloud: confirm account + home region (Riyadh me-riyadh-1, fallback Jeddah). Create Ampere A1
   VM (2 OCPU / 12 GB, Ubuntu 24.04). Budget alert.
2. Server hardening: SSH key only, no root login, firewall (80/443 + SSH from my IP), fail2ban,
   unattended upgrades.
3. Dockerfiles: backend (python:3.11-slim, gunicorn + uvicorn worker), frontend (next build/start).
   Must build for arm64.
4. infra/docker-compose.prod.yaml: caddy, frontend, backend, worker, beat, postgres 17, redis 7.
   Caddyfile: /api, /ws, /admin -> backend; rest -> frontend; HTTPS automatic.
5. Celery app (config/celery.py) + Channels ASGI routing if not done yet.
6. GitHub Actions CI on PRs: ruff, pytest (Postgres service), eslint, prettier check, tsc, next build.
7. CD on merge to main: buildx arm64 -> GHCR -> SSH deploy (compose pull/up, migrate, health check).
8. Nightly pg_dump backup script -> encrypted -> OCI Object Storage (other KSA region).
9. python manage.py check --deploy clean; staging URL works with login.
10. Update docs (development.md deploy section, roadmap), PR.

Design reference: docs/architecture.md section 9, ADR-0004, docs/security.md section 8.
```

---

## Part C — End of day (paste before leaving)
```
We're stopping for today. Check git status, tell me what is uncommitted, and give me the exact
commands to commit and push. Then summarise in 5 lines what we finished and what is next,
so I can continue on the other machine.
```
