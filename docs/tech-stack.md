# Tech Stack

_Decided 2026-10-30. Pin exact versions in `backend/requirements/*.txt` / `package.json` at project setup._

Guiding principles for this project:
- **One developer + AI agent** → boring, well-documented, popular tools (AI writes better code for them), few moving parts.
- **$20/month** → everything runs on one VM at launch; no paid managed services.
- **Grow without a rewrite** → modular monolith, clean module boundaries, adapters for third parties.

## Stack at a glance

| Layer | Choice | Alternative (and when to pick it) |
|---|---|---|
| Backend | **Django 5.2 LTS + Django REST Framework**, Python 3.11 (same version locally and in the Docker image) | FastAPI — only if the backend becomes a thin API with no need for Django's auth/admin/ORM |
| Python packages | **pip + venv**, pinned `requirements/{base,dev,prod}.txt` | uv / Poetry — not needed for one developer |
| API contract | **drf-spectacular** (OpenAPI) → generated TypeScript client | Hand-written fetch wrappers — not worth it |
| Frontend | **Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui (Base UI)**, with `lucide-react` icons, IBM Plex Sans and IBM Plex Sans Arabic | Vite + React SPA + separate Astro marketing site — if SSR ever becomes a burden |
| i18n | **next-intl** (frontend), Django i18n (emails/PDFs) | — |
| 2FA QR code | **qrcode.react**, loaded only on the setup step | — |
| Database | **PostgreSQL 17** | — (no serious alternative for this workload) |
| Multi-tenancy | **Shared schema, `school_id` on every tenant row** | `django-tenants` (schema per school) — if a large customer demands stronger isolation or per-school customisation |
| Cache / broker | **Redis 7** (or Valkey) | — |
| Background jobs | **Celery + Celery Beat** | Django-Q2 / Dramatiq — lighter, but smaller ecosystem |
| Real-time | **Django Channels + channels-redis** (WebSockets) | Server-Sent Events — if you only ever need server→client push |
| Auth | **Django sessions (httpOnly cookies)**, django-otp (TOTP 2FA), custom email OTP, argon2, django-axes | JWT (simplejwt) — only if a native mobile app is added |
| Authorization | Membership-based roles + policy functions + scoped selectors | django-rules — if policies grow very complex |
| Audit log | **django-auditlog** | Custom `AuditEvent` model |
| PDF | **WeasyPrint** (handles Arabic shaping + RTL) with Arabic fonts | Headless Chromium (Playwright) — if layouts get very complex |
| File storage | **OCI Object Storage (S3-compatible) via django-storages**, private bucket + presigned URLs | Local disk volume — acceptable for the first days only |
| Search | **PostgreSQL full-text + pg_trgm** | Meilisearch — at 100K+ users if name search gets slow |
| Email (sending) | **SMTP through Django**, settings in `.env`, behind `apps/integrations/email` | `django-anymail` + Amazon SES or Brevo, if volume or delivery becomes a problem |
| Email (mailbox) | **Zoho Mail free** (info@, sales@) | Google Workspace — if the client wants Gmail |
| Hosting | **Oracle Cloud (OCI) Riyadh `me-riyadh-1`**, 1 Ampere A1 VM | Local Saudi VPS (Wafai Cloud etc.) or AWS Saudi region (launching Dec 2026) |
| Runtime | **Docker Compose + Caddy** (auto HTTPS) on Ubuntu 24.04 — servers only | Nginx + certbot — you know it, but Caddy is less config |
| Staging | **Hostinger VPS (France), test data only**, behind the existing nginx. See [ADR-0011](decisions/0011-staging-on-hostinger-behind-shared-nginx.md) | — |
| Static files | **WhiteNoise**, production settings only. See [ADR-0012](decisions/0012-whitenoise-for-static-files.md) | Serve from the proxy or object storage, if traffic to these files grows |
| Local dev | **Fully native on both machines:** PostgreSQL 17 installed natively, no Docker, no Redis. See [development.md](development.md) / [ADR-0009](decisions/0009-local-development-fully-native.md) | — |
| CI/CD | **GitHub Actions → GHCR → SSH deploy** | — |
| Errors | **Sentry** (free tier, PII scrubbing on) | GlitchTip self-hosted — if no data may leave KSA, even error traces |
| Uptime | **UptimeRobot / Better Stack free** (external) | — |
| Logs | Docker JSON logs with rotation + structured logs (structlog) | Grafana Loki — at 10K+ users |
| AI (Phase 3) | **Provider adapter**, self-hosted open-weight model on a dedicated (paid) GPU server once funded | Larger self-hosted model as budget grows. Never a third-party hosted API — client decision ([ADR-0014](decisions/0014-self-hosted-ai-model.md)) |

## Why each choice fits this project

**Django + DRF.** You already know Django well. A school system is data-heavy CRUD with lots of relations and permissions, and Django ships with auth, permissions, ORM, migrations, an admin panel (handy as an internal Super Admin tool) and i18n. That saves days in a 4-week sprint. DRF is the most widely used Django API framework, so AI agents produce reliable code for it.

**Next.js.** One codebase covers three things: the SEO marketing site (static/SSR pages), the logged-in app and the PWA. You already use it with AI. shadcn/ui + Tailwind give fast, consistent UI, and Tailwind's logical-property utilities make RTL straightforward.

**Shared-schema multi-tenancy.** At 1–50 schools, one schema with a `school_id` column is the simplest model: one migration run, simple backups, easy cross-school reporting for the Super Admin. Isolation is enforced in code (base model + scoped selectors + tests). PostgreSQL Row-Level Security can be added later as a second safety net without changing the data model. Details: [ADR-0002](decisions/0002-multi-tenancy-shared-schema.md).

**PostgreSQL.** Strongly relational data (students ↔ sections ↔ subjects ↔ marks), reporting queries and transactions for fees. JSONB covers flexible bits (report card templates, settings).

**Celery + Redis.** Report card PDFs for a whole class, bulk attendance emails, quotation emails and nightly backups must not run inside a web request. Celery is the standard choice, and Redis also serves as the cache and the Channels layer, so one service does three jobs.

**Channels.** Live notifications and teacher–parent messaging need WebSockets. Channels stays inside the same Django codebase, so you get the same auth and the same models.

**Session cookies instead of JWT.** The browser is the only client (web + PWA). httpOnly session cookies can't be read by injected JavaScript, logout and revocation are instant, and Django handles CSRF. Caddy serves frontend and API on the **same origin** (`/api`, `/ws` → Django), so there is no CORS and no token storage problem.

**WeasyPrint.** Report cards, receipts and quotations must render Arabic correctly. WeasyPrint shapes Arabic text and supports `direction: rtl`, using HTML/CSS templates you already know.

**Oracle Cloud Riyadh.** It is one of the few options with a region **inside KSA** that fits $20/month. Oracle has two Saudi regions (Jeddah `me-jeddah-1`, Riyadh `me-riyadh-1`), so backups can go cross-region and still stay in KSA. Always Free Ampere A1 now gives **~2 OCPU / 12 GB RAM** (Oracle halved it in mid-2026), which is plenty for launch. Use a **Pay-As-You-Go account**: free allowances still apply, but instances are not reclaimed as "idle" and you can buy more capacity instantly. Details: [ADR-0004](decisions/0004-hosting-oracle-cloud-saudi.md).

**Docker Compose + Caddy.** You already deploy with Docker. Compose on one VM is enough up to ~10 schools. Caddy handles TLS certificates automatically.

## Trade-offs and risks

| Risk | Impact | Mitigation |
|---|---|---|
| Shared schema → a missed filter leaks data across schools | **Critical** (trust + PDPL) | `TenantModel` + scoped selectors only; cross-tenant test for every endpoint; add Postgres RLS in hardening |
| Oracle A1 "out of capacity" in Riyadh/Jeddah | Can't get free VM | Try both regions and retry; fallback paid OCI AMD shape or Saudi VPS (~$30–60/month — over budget, tell the client) |
| Single VM = single point of failure | Downtime if VM dies | Daily off-VM backups in second KSA region; infra as scripts so a rebuild takes <1 hour; documented restore |
| ARM (A1) images | Some Python wheels missing | All chosen deps support arm64; build multi-arch images in CI with buildx |
| Two frameworks (Django + Next.js) for one dev | More context switching | Generated TS API client keeps them in sync; strict folder conventions |
| Sentry / SES are outside KSA | PDPL cross-border transfer concerns | No PII in error events (`send_default_pii=False`, scrubbing); emails contain minimal data + link to app; switch to GlitchTip / KSA email provider if a customer requires it |
| Celery adds operational weight | More containers | Same image, different command; only 2 extra containers |
| 4-week deadline | Cut corners on security | Cut **features**, never isolation, auth, backups or HTTPS |

## Estimated monthly cost at launch

| Item | Cost |
|---|---|
| OCI Ampere A1 VM (2 OCPU / 12 GB) — Always Free allowance | $0 |
| Block storage (≤200 GB) + Object Storage (≤20 GB) — Always Free | $0 |
| Domain (.com) | ~$1 |
| Amazon SES (~10K emails) | ~$1 |
| Zoho Mail free, Sentry free, UptimeRobot free, GitHub free | $0 |
| **Total** | **~$2–5 / month** |

### Phase 3 add-on: self-hosted AI (lesson plans/presentations)

Not needed until Phase 3 AI work starts ([ADR-0014](decisions/0014-self-hosted-ai-model.md)). Kept separate from the Always Free VM above — the main app stays on Oracle, the AI model runs on a rented GPU, billed separately.

| Item | Cost |
|---|---|
| GPU rental — RTX 4090 (24 GB VRAM), [DCP.sa](https://dcp.sa) (Saudi Arabia, per-second billing, PDPL-compliant) | 3.62 SAR/hr (~$0.97/hr) while running |
| Light/occasional use (e.g. ~1,000 generations/month, GPU only on for the request) | ~$16–30/month |
| Moderate use (several schools, daily use) | ~$80–100/month |
| Always-on 24/7 (not recommended — needs start/stop automation instead) | ~$700/month |
| **Project total once AI is live** | **~$22–100 / month** (app ~$2–5 unchanged + AI add-on) |

Model: a 7–14B parameter open-weight model (e.g. Qwen 2.5 14B) fits comfortably in 24 GB VRAM — no training needed to start, good prompts are enough; fine-tuning on the school's own sample lesson plans is a later, optional quality improvement.

Leaves headroom inside the $20 budget. Not included: developer tooling (Claude subscription) and a `.sa` domain if the client wants one.
If free A1 capacity is unavailable, expect **~$30–60/month** for a paid VM in KSA. Check current prices in the provider's console before buying.

Sources consulted for hosting facts (2026-10): [OCI Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm), [OCI Riyadh region release note](https://docs.oracle.com/iaas/releasenotes/changes/45cb2bf5-290f-40fb-af89-b7b9455f35fe/index.htm), [InfoQ on 2026 free tier cut](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/), [AWS Saudi region Dec 2026](https://www.aboutamazon.com/news/aws/aws-cloud-region-saudi-arabia), [Saudi VPS listings](https://www.whtop.com/plans/wafaicloud.com/130656).
