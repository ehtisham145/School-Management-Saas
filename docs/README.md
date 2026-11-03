# Project Docs — School Management SaaS (KSA)

Multi-tenant School Management System sold as SaaS to private schools in Saudi Arabia.
One platform, many schools; each school's data is fully isolated.

## Read in this order

| Doc | What it answers |
|---|---|
| [requirements.md](requirements.md) | What we are building, for whom, at what scale |
| [tech-stack.md](tech-stack.md) | Chosen technology per layer, why, alternatives, cost |
| [architecture.md](architecture.md) | How the system fits together: tenancy, auth, RBAC, jobs, real-time, deployment, folder structure |
| [security.md](security.md) | Security and PDPL essentials — non-negotiable rules |
| [roadmap.md](roadmap.md) | 4-week MVP plan, then hardening, features, scaling |
| [development.md](development.md) | Local setup (laptop / desktop), git workflow, commits, PRs, CI, "definition of done" |
| [decisions/](decisions/) | Architecture Decision Records (ADRs) — one decision per file |
| [../design/](../design/) | Approved visual design: demo page, brand assets and the frontend brief |

## Rules for anyone (human or AI agent) writing code here

1. **Every tenant-owned model inherits `TenantModel`** and every query goes through a school-scoped selector. Never query a tenant model with `Model.objects` directly in views. See [ADR-0002](decisions/0002-multi-tenancy-shared-schema.md).
2. **Business logic lives in `services.py` (writes) and `selectors.py` (reads)**, not in views or serializers.
3. **Dates are stored Gregorian**, Hijri is display-only. See [ADR-0005](decisions/0005-dates-gregorian-storage-hijri-display.md).
4. **All UI text goes through i18n** (Arabic + English). Use CSS logical properties (`ms-*`, `pe-*`), never `left`/`right`. See [ADR-0006](decisions/0006-bilingual-arabic-english-rtl.md).
5. **Third-party services sit behind an adapter** (email, payments, AI). See [ADR-0007](decisions/0007-integrations-behind-adapters.md).
6. **Every new endpoint ships with a cross-tenant test** proving School A cannot read or write School B's data.
7. A new significant decision gets a new ADR; don't silently change an old one — supersede it.
