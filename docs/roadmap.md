# Roadmap

_Start: early Nov 2026. Developer: 1 person + AI coding agent, ~7–8 focused hours/day._
_Rule for the sprint: **cut features, never security** (isolation, auth, backups, HTTPS)._

## Phase 1 — MVP (Weeks 1–4)

Goal: one or two real schools can run daily operations.

### Week 1 — Foundation
- [ ] Monorepo, `CLAUDE.md`, pre-commit (ruff, eslint, prettier), `.env.example`
- [ ] Local dev in both modes ([development.md](development.md)): laptop without Docker, desktop with `docker-compose.dev.yml` (Postgres + Redis)
- [ ] Django project, settings split, Postgres, Celery, Channels wired; Redis optional via `REDIS_URL`
- [ ] `TenantModel`, `TenantMiddleware`, `TenantScopedViewSet`, policies, cross-tenant test fixture
- [ ] Accounts: User, email/password, username/password, email OTP, TOTP 2FA, axes, throttling
- [ ] Membership + roles, school switcher
- [ ] Super Admin: create school + its admin (Django admin is acceptable for week 1)
- [ ] Next.js app: `[locale]` routing, RTL/LTR layouts, shadcn base, login flows, generated API client
- [ ] OCI VM provisioned, Caddy, CI pipeline, **staging live**

### Week 2 — Academics core
- [ ] Academic years, terms, grades, sections, subjects
- [ ] Users management: teachers, students (bulk import from Excel/CSV), parents + guardianship
- [ ] Teacher assignments, enrollment
- [ ] Timetable
- [ ] Attendance (teacher marks per section; principal/admin overview; parent view)
- [ ] Role dashboards (simple stat cards)

### Week 3 — Academics depth
- [ ] Exams, exam subjects, marks entry, grade scale
- [ ] Report card PDF (WeasyPrint, Arabic + English) — per student and bulk via Celery
- [ ] Homework: create with attachments, student submission, teacher grading
- [ ] Fees: fee heads, structures, dues, manual payment recording, receipt PDF, outstanding report

### Week 4 — Communication + go-live
- [ ] Announcements (school / grade / section / role audiences)
- [ ] Teacher–parent messaging
- [ ] In-app notifications live via WebSocket; email notifications via Celery
- [ ] Hijri + Gregorian date display everywhere
- [ ] Audit log wired on sensitive models
- [ ] Security checklist ([security.md](security.md) §9), backups + restore test, Sentry, uptime monitor
- [ ] **Production deploy**, onboard pilot school, training session

If week 3 slips, move **homework** to month 2 first, then **messaging** (announcements stay).

## Phase 1.5 — SaaS layer (Weeks 5–8)
- [ ] Super Admin UI in Next.js: schools, plans, subscriptions (manual activate/expire), usage overview
- [ ] Quotation builder → PDF → email to school's business email; quotation status tracking
- [ ] Public marketing site: home, features, pricing, about, contact, **demo request** → Super Admin inbox + email
- [ ] SEO: metadata, Arabic/English `hreflang`, sitemap, Open Graph, fast static pages
- [ ] PWA: manifest, service worker, install prompt, Web Push
- [ ] Privacy policy, terms, DPA template
- [ ] Polish from pilot school feedback

## Phase 2 — Hardening (Month 3)
- [ ] PostgreSQL Row-Level Security as a second isolation layer
- [ ] Load test the 07:30 attendance peak (e.g. k6 against 10 simulated schools)
- [ ] Slow-query review, indexes, Redis caching for dashboards
- [ ] File virus scanning (ClamAV)
- [ ] Separate staging VPS; automated backup restore verification
- [ ] Legal review of PDPL documents
- [ ] Data export + school offboarding (deletion) flow

## Phase 3 — Features (Month 4+)
- [ ] Lesson plans + presentations: manual editor (rich text + slide builder)
- [ ] AI generation behind `integrations/ai` adapter, per-school monthly quota, async via Celery. No student PII sent to the model ([ADR-0007](decisions/0007-integrations-behind-adapters.md))
- [ ] Online classes — integrate an existing provider (e.g. Jitsi / Zoom / Google Meet links) rather than building video
- [ ] Online fee payments via a Saudi gateway (Moyasar / HyperPay / Tap) — if the client asks
- [ ] Client-requested features

## Phase 4 — Scaling (as schools grow)
Follow the triggers in [architecture.md §11](architecture.md#11-scaling-path): own DB server at ~10 schools, load balancer + multiple app VMs + read replica at ~50 schools.

## Milestones

| Date (target) | Milestone |
|---|---|
| End of Week 1 | Staging live, login for all roles working |
| End of Week 4 (~early Dec 2026) | MVP in production, pilot school onboarded |
| End of Month 2 (~early Jan 2027) | Marketing site, quotations, PWA — ready to sell |
| Month 3 | Hardening complete |
| Before Aug 2027 | Sales push for the new Saudi academic year |
