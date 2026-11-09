# ADR-0014: Self-hosted AI model for lesson-plan generation, not a third-party API

- **Status:** Accepted
- **Date:** 2026-11-08

## Context
[ADR-0007](0007-integrations-behind-adapters.md) left the AI provider for lesson-plan/presentation generation undecided ("hosted API vs. self-hosted model"). The client has now decided: the model must be **self-hosted**, never a third-party API. No further discussion needed on this point — this ADR records the decision and its practical consequences.

The current infrastructure plan ([ADR-0004](0004-hosting-oracle-cloud-saudi.md)) is a single free-tier Oracle Ampere A1 VM: 2 OCPU / 12 GB RAM, **no GPU**. Running an AI model there, alongside the live Django/Next.js/Postgres/Celery stack serving real schools, is not practical — no GPU means slow inference, and the model's RAM footprint would compete with the production app on a box that only has 12 GB total.

## Decision
- The AI feature (Phase 3, lesson plans/presentations) will **always** use a self-hosted open-weight model, accessed through the existing `apps/integrations/ai/` adapter ([ADR-0007](0007-integrations-behind-adapters.md)). Never a hosted third-party LLM API.
- Staged rollout:
  1. **Now:** stay on the free-tier Oracle VM for the main app. The AI feature is **not enabled** — there is no inference server yet, and the free VM is not fit to host one alongside production traffic.
  2. **Before the AI feature launches:** rent a **separate GPU server dedicated to model inference** — a 24 GB VRAM GPU (e.g. RTX 4090) comfortably runs a 7–14B parameter open-weight model (e.g. Qwen 2.5 14B), which is the target size for quality without overspending. Recommended provider: [DCP.sa](https://dcp.sa) — GPU rental physically hosted in Saudi Arabia with per-second billing, so data/model/compute all stay in-Kingdom (PDPL) and cost scales with actual use rather than running 24/7. See [tech-stack.md](../tech-stack.md#phase-3-add-on-self-hosted-ai-lesson-plans-presentations) for the cost table. It stays a separate server from the main app VM so slow or busy inference never degrades attendance/fees/exams for schools already using the platform.
  3. The adapter is what the rest of the codebase calls — swapping the exact model or inference server later is a config change, not a rewrite.
- Unchanged from ADR-0007: generation runs in Celery, per-school monthly quota, no student PII in prompts (grade/subject/topic/curriculum hints only), output is a draft the teacher edits.

## Consequences
- ✅ No per-token/per-request cost to a third party; no lesson content leaves infrastructure the project controls — matches the client's requirement directly.
- ✅ The adapter boundary means the AI work already planned in `apps/integrations/ai/` doesn't change shape — only which implementation sits behind it.
- ⚠️ A dedicated GPU server is a **new, real monthly cost** once this launches, outside the original ~$20/month budget in [tech-stack.md](../tech-stack.md). Estimated ~$16–100/month depending on usage (light to moderate), or ~$700/month if left running 24/7 instead of started/stopped per use — must be budgeted with the client before Phase 3 AI work starts.
- ⚠️ The AI feature is **gated on that server existing** — app-side code can be built ahead of time, but the feature can't go live on the free-tier VM alone.
- ⚠️ Model quality/speed is a direct function of whatever GPU budget is eventually approved — this is a trade-off the client is accepting in exchange for not using a third-party API.
