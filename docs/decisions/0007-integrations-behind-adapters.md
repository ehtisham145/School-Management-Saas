# ADR-0007: Email, payments and AI behind adapters

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Several integrations are uncertain or deferred: fees are cash today (an online gateway may come later), and email providers may change for cost or data-residency reasons. The AI provider for lesson plans was originally undecided (hosted API vs. self-hosted model) — **resolved by [ADR-0014](0014-self-hosted-ai-model.md): always self-hosted, never a third-party API.**

## Decision
Every external service is accessed through a small interface in `backend/apps/integrations/<kind>/`. Business code calls the interface, never a vendor SDK.

| Kind | MVP implementation | Later options |
|---|---|---|
| Email | Django SMTP, settings in `.env` | `django-anymail` with Amazon SES or Brevo; a KSA-based provider if a customer requires it |
| Payments | `ManualPaymentProvider` (record cash/bank transfer, issue receipt) | Moyasar / HyperPay / Tap (Mada, Apple Pay, STC Pay) |
| AI (Phase 3) | Self-hosted open-weight model on a dedicated GPU server, once funded — see [ADR-0014](0014-self-hosted-ai-model.md) | Larger/different self-hosted model as budget grows. Not a third-party API, by client decision |

AI rules:
- Generation runs in Celery, never in the request.
- Per-school monthly quota (requests/tokens) stored in `SchoolSettings`, checked before calling.
- Prompts contain **no student personal data** — only grade, subject, topic and curriculum hints.
- Output is a draft the teacher edits; it is sanitised before storage.

## Consequences
- ✅ Switching vendors is a config change plus one adapter class.
- ✅ AI cost is visible and capped per school.
- ⚠️ A small amount of extra code up front (interfaces + one implementation each).
