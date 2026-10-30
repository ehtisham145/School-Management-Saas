# ADR-0002: Multi-tenancy — shared database, shared schema, `school_id` column

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Many schools on one platform; each school's data must be invisible to others. Expected 1–2 schools at launch and ~50 within three years. A Super Admin needs cross-school views (subscriptions, usage).

## Decision
- One PostgreSQL database, one schema. Every tenant-owned table has a non-null, indexed `school_id` FK, via the abstract `TenantModel`.
- The current school comes **only** from the authenticated session's membership (`request.school`).
- Isolation is enforced by scoped selectors, a base `TenantScopedViewSet`, FK validation in serializers, per-school unique constraints, and a mandatory cross-tenant test per endpoint.
- Later (hardening phase): PostgreSQL Row-Level Security policies keyed on `current_setting('app.current_school')` as a second layer.

## Consequences
- ✅ Simplest to build, migrate, back up and report on; one migration run for all schools.
- ✅ Works comfortably to hundreds of schools with proper indexes.
- ⚠️ A missing filter is a data leak → mitigated by the layers above and by tests; this is the project's #1 code-review focus.
- ⚠️ A noisy school affects others → monitor; move very large customers to a dedicated DB if needed.

## Alternatives considered
- **Schema per school (`django-tenants`):** stronger isolation, but N× migrations, harder cross-school reporting, more complex tooling. Revisit if a customer contractually requires it.
- **Database per school:** strongest isolation, highest ops cost. Only for a future enterprise tier.
