# ADR-0001: Modular monolith — Django + DRF backend, Next.js frontend

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
A single developer working with an AI agent must deliver a multi-tenant school SaaS in ~4 weeks on a ~$20/month budget, and the design must still grow to ~50 schools / 100K accounts. The developer is strongest in Django/FastAPI and uses Next.js with AI help.

## Decision
- Backend: **Django 5.2 LTS + Django REST Framework**, one deployable, features split into Django apps with a `services.py` / `selectors.py` layering.
- Frontend: **Next.js (App Router, TypeScript)** serving the marketing site, the logged-in app and the PWA from one codebase.
- API contract via **drf-spectacular** OpenAPI → generated TypeScript client.
- No microservices.

## Consequences
- ✅ Django's built-in auth, ORM, migrations, admin and i18n save significant time.
- ✅ One backend language; well-known frameworks → more reliable AI-generated code.
- ✅ Module boundaries allow extracting a service later if ever needed.
- ⚠️ Two runtimes (Python + Node) to deploy — handled by Docker Compose.
- ⚠️ Module discipline must be enforced by convention (no cross-app model imports in views).

## Alternatives considered
- **FastAPI backend:** more modern async, but we would rebuild auth, admin, permissions and migrations by hand. Rejected for the timeline.
- **Django templates + HTMX only:** fastest for CRUD, but weaker for PWA, rich editors (lesson plans) and the SEO marketing site in one place.
- **Microservices:** unjustified at this scale and team size.
