# ADR-0016: Interim — hosted LLM API (Groq/Gemini) for lesson-plan generation, self-hosted deferred

- **Status:** Accepted
- **Date:** 2026-11-09

## Context
[ADR-0014](0014-self-hosted-ai-model.md) committed to a self-hosted model only, never a third-party API, and priced a dedicated GPU server (recommended: [DCP.sa](https://dcp.sa), Saudi Arabia) at roughly $16–100/month depending on usage, or up to ~$700/month if run without start/stop automation.

That is a real, ongoing cost the project isn't ready to carry before launch — there's no paying school yet, and Phase 3 (where this feature lives) is still months away. Committing to a rented GPU server now, for a feature not yet built, doesn't fit the "cut features, never security" / lean-launch posture the rest of the roadmap follows.

## Decision
- **Interim:** Phase 3 AI generation (lesson plans/presentations) launches on a **hosted LLM API** (e.g. Groq or Gemini — exact provider picked at implementation time) instead of a self-hosted model.
- **Not a reversal of intent, a sequencing change:** self-hosting remains the target once there's budget to justify a dedicated GPU server (e.g. after the first paying schools, or when the client funds it directly). Revisit this ADR at that point.
- Still behind the `apps/integrations/ai/` adapter ([ADR-0007](0007-integrations-behind-adapters.md)) — switching from a hosted API to a self-hosted model later is a new adapter implementation, not a rewrite of the calling code.
- Unchanged rules: generation runs in Celery, per-school monthly quota, **no student PII in prompts** (grade/subject/topic/curriculum hints only), output is a teacher-edited draft.
- New trade-off this introduces: lesson content (not student PII, but still school-authored content) now leaves Oracle/KSA infrastructure and goes to a US-based vendor (Google/Groq) for processing. This is a conscious compromise, inconsistent with the project's general PDPL/data-residency posture elsewhere — flag this to the client when the AI feature is actually built, in case they want to weigh in before launch.

## Consequences
- ✅ No GPU server cost until the feature is real and used — pay-per-token instead, estimated ~$1–15/month at expected launch volume (cheap commercial models), scaling with actual usage rather than a fixed server bill.
- ✅ Better output quality than a small self-hosted model would give at a comparable budget.
- ⚠️ **Supersedes [ADR-0014](0014-self-hosted-ai-model.md)'s "never a third-party API" stance for the interim period** — driven by cost reality, not a change of preference. ADR-0014 stays the long-term target.
- ⚠️ Data residency trade-off (see above) — needs an explicit client conversation before Phase 3 ships, not just a developer call.
- ⚠️ Vendor dependency (API pricing/availability changes) until self-hosting happens.
