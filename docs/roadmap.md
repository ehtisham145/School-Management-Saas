# Roadmap

_Start: early Nov 2026. Developer: 1 person + AI coding agent, ~7–8 focused hours/day._
_Rule for the sprint: **cut features, never security** (isolation, auth, backups, HTTPS)._

## Phase 1 — MVP (Weeks 1–4)

Goal: one or two real schools can run daily operations.

### Week 1 — Foundation
- [x] Monorepo, `CLAUDE.md`, pre-commit (ruff, eslint, prettier), `.env.example`
- [x] Local dev fully native on both machines ([development.md](development.md), [ADR-0009](decisions/0009-local-development-fully-native.md)): Postgres 17 installed natively, no Docker, no Redis on either machine
- [x] Django project, settings split, Postgres, ruff + pytest; Redis optional via `REDIS_URL`
- [x] Celery app (`config/celery.py`) wired, email adapter (`apps/integrations/email`, `feature/totp-2fa`)
- [ ] Channels ASGI routing wired
- [x] `TenantModel`, `TenantMiddleware`, `TenantScopedViewSet`, cross-tenant test fixture (`feature/multi-tenancy`)
- [x] `apps/core/policies.py` permission matrix (`can(role, action)`) + `HasPolicy` on `TenantScopedViewSet` (`feature/policies`)
- [x] Accounts: custom `User` model (`apps/accounts`)
- [x] Accounts: username/password login + logout (`POST /api/auth/login/`, `/logout/`)
- [x] Accounts: login lockout (`django-axes`, 15 attempts/1h cool-off, raised from 5) + throttling (`feature/login-lockout`)
- [x] Accounts: email OTP (parents), TOTP 2FA + email-based reset (staff, `feature/totp-2fa`) — 2FA removed later ([ADR-0018](decisions/0018-remove-two-factor-authentication.md))
- [x] Membership + roles (`apps/tenancy`)
- [x] School switcher (`POST /api/auth/switch-school/`)
- [x] Super Admin: create school + its admin (Django admin, `feature/django-admin`)
- [x] Next.js 16 app: `[locale]` routing (next-intl, default `en`), RTL/LTR layouts, Arabic font, shadcn/ui base (RTL), Prettier
- [x] Login flow UI (Next.js): username/password form, multi-school picker, placeholder dashboard + logout (`feature/login-flow`)
- [x] Login flow UI: email code and 2FA verify/reset steps, session restored after refresh via `GET /api/auth/me/`, only school activated automatically, standard API error format (`fix/login-active-school`) — 2FA steps removed later ([ADR-0018](decisions/0018-remove-two-factor-authentication.md))
- [x] CI pipeline: GitHub Actions runs backend and frontend checks on every PR (`chore/ci`)

**Next, in this order** (Super Admin panel moved up from Phase 1.5 so school onboarding can be shown to the client, decided 2026-11-03):
- [x] 2FA setup page (`/2fa/setup/`, `/2fa/confirm/`) and mandatory 2FA for Super Admins and School Admins (`feature/platform-panel`) — 2FA removed later ([ADR-0018](decisions/0018-remove-two-factor-authentication.md))
- [x] Two-factor authentication removed from the backend and the website at the owner's request; login lockout raised to 15 attempts ([ADR-0018](decisions/0018-remove-two-factor-authentication.md))
- [x] Super Admin login on the website: login and `/me` identify `is_platform_admin`, redirect to `/platform`
- [x] Super Admin APIs (`/api/platform/schools/`): list schools, create a school + its admin, other roles denied. Actions go to the application log for now; move to `django-auditlog` with the Week 4 audit item
- [ ] Django admin (`/admin`) accepts a password alone: restrict it before launch
- [x] Super Admin panel (Next.js `/platform`): schools list and new-school form, Arabic + English
- [x] Super Admin panel layout: sidebar, top bar with language and profile menus, dashboard, profile page (`feature/platform-admin-panel`)
- [x] Super Admin demo requests: list, search, status pipeline, notes, create a school from a request
- [x] Super Admin schools: list, search, active and inactive counts, details, activate and deactivate (a deactivated school's users lose access)
- [x] New school form: onboarding details, field validation, live warnings on number fields, scroll to the first error
- [x] Welcome reveal after a fresh sign-in: greeting, panels sliding apart, Skip and Esc, reduced motion, Arabic and English
- [ ] School app layout (sidebar, top bar) + Academic Year screen
- [ ] Generated API client (OpenAPI), with the first screen that benefits from typed APIs

- [x] Interim staging live at `staging.lessonlab.me`, test data only, auto-deployed from `main` ([ADR-0013](decisions/0013-staging-auto-deploy.md))
- [ ] Staging moved from Hostinger to an OCI trial VM with its own Caddy ([ADR-0015](decisions/0015-staging-on-oci-trial-with-caddy.md)). Trial ends ~2026-12-07, so plan the next move before then

**Waiting on the client's hosting:**
- [ ] OCI VM provisioned, Caddy, **staging live**. Needed at least 1 week before launch, because Redis, Celery workers and WebSockets can only be verified there ([ADR-0009](decisions/0009-local-development-fully-native.md))

### Week 2 — Academics core
- [x] Academic years API + Term models and services (`feature/academics`)
- [ ] Term API, grades, sections, subjects
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
- [ ] Super Admin panel additions: plans, subscriptions (manual activate/expire), usage overview (schools list and onboarding moved to Week 1)
- [ ] Quotation builder → PDF → email to school's business email; quotation status tracking
- [x] Public marketing site rebuilt to the approved design (`design/`): Home, About Us, LMS, Pricing (sample prices), Contact, Arabic and English, RTL, language menu (`feature/brand-home-redesign`)
- [x] Book a demo and Contact forms: saved through `/api/platform/demo-requests/` and `/contact-messages/`, listed in Django admin, emailed to `LEADS_EMAIL`
- [x] Site effects: typewriter on every page heading, cards slide into place on scroll, status cards on each hero (`feature/brand-home-redesign`)
- [x] Forms: required-field asterisks, live validation that clears at once, scroll to the first error, Saudi mobile validation on the frontend and backend, compact Book a demo popup (`feature/forms-validation`)
- [x] Sign in page: brand beside a sign-in card on a plain page, no image, Book a demo link, validation on every step
- [x] SMTP email settings through `.env`; `sendtestemail` ran without an error against the real provider. Inbox delivery and SPF/DKIM/DMARC still to be confirmed
- [ ] Replace sample prices and plan contents with confirmed ones
- [ ] Translate backend validation and email text into Arabic
- [x] SEO: page metadata and Arabic/English `hreflang`, server-rendered text
- [ ] SEO: sitemap, Open Graph images
- [ ] PWA: manifest, service worker, install prompt, Web Push
- [x] Privacy policy page `/privacy` (Arabic + English), linked from the footer. It is a draft until the legal review below
- [ ] Terms, DPA template
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
- [ ] AI generation behind `integrations/ai` adapter, per-school monthly quota, async via Celery. No student PII sent to the model. **Interim: hosted API (Groq/Gemini)** — self-hosted model is the long-term target once a dedicated GPU server is funded ([ADR-0016](decisions/0016-interim-hosted-ai-api.md), [ADR-0014](decisions/0014-self-hosted-ai-model.md))
- [ ] Online classes — integrate an existing provider (e.g. Jitsi / Zoom / Google Meet links) rather than building video
- [ ] Online fee payments via a Saudi gateway (Moyasar / HyperPay / Tap) — if the client asks
- [ ] Client-requested features

## Phase 4 — Scaling (as schools grow)
Follow the triggers in [architecture.md §11](architecture.md#11-scaling-path): own DB server at ~10 schools, load balancer + multiple app VMs + read replica at ~50 schools.

## Milestones

| Date (target) | Milestone |
|---|---|
| End of Week 1 | Login for all roles working (done). Staging moved: it waits for the client's hosting |
| End of Week 4 (~early Dec 2026) | MVP in production, pilot school onboarded |
| End of Month 2 (~early Jan 2027) | Marketing site, quotations, PWA — ready to sell |
| Month 3 | Hardening complete |
| Before Aug 2027 | Sales push for the new Saudi academic year |
