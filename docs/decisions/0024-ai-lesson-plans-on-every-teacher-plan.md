# ADR-0024: AI lesson plans on every teacher plan, reviewed before saving

- **Status:** Accepted
- **Date:** 2026-11-19
- **Amends:** [ADR-0022](0022-teacher-classroom-app.md) (plan limits table)

## Context
In ADR-0022 only Teacher Pro could write lesson plans with AI. Teachers today expect AI lesson plans from the start, and a trial without them doesn't show the product's main value. A saved AI plan was also stored straight away, so the teacher could not check it first.

## Decision
- Every teacher plan includes AI lesson plans. The limits in `apps/classroom/entitlements.py` are now:

  | | Free trial | Teacher | Teacher Pro |
  |---|---|---|---|
  | Classes | 2 | 5 | No limit |
  | Students | 30 | 100 | No limit |
  | Lesson plans | 20 | No limit | No limit |
  | PowerPoint downloads | 10, with a small mark | No limit | No limit |
  | AI lesson plans | 10 for the whole trial | 30 a month | 100 a month |
  | Report cards, parent messages | No | No | Yes |

- `POST /api/classroom/lesson-plans/generate/` returns a draft and saves nothing but the count. The teacher reads and edits it, then saves it with the normal create call and `source: "ai"`. Each draft counts, even one that is not saved, because the provider was paid for it.
- No draft is made when the plan has no room for another lesson plan.
- At most 3 free trials can start from one IP address in 24 hours, counted from the audit log, so one person can't start trial after trial with new email addresses.

## Consequences
- More AI requests reach the provider. The `lesson_ai` throttle (20 an hour per user) still applies.
- Report cards and parent messages stay in Teacher Pro.
- A school or office sharing one IP address can start only 3 trials a day; others are asked to try the next day.
