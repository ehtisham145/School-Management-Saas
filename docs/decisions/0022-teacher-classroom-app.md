# ADR-0022: The individual teacher's classroom app

- **Status:** Accepted
- **Date:** 2026-11-18
- **Amended by:** [ADR-0024](0024-ai-lesson-plans-on-every-teacher-plan.md) (AI on every plan, new trial limits)

## Context
[ADR-0021](0021-individual-teacher-workspace-and-trial.md) lets a teacher sign up and start a trial. The teacher now needs a working product: classes, students, lesson plans, presentations, attendance, marks, plan limits and a way to upgrade. Client decisions on trial limits, payment and data retention are still open, so the suggested values are used and kept in one place.

## Decision
- A new `apps/classroom` app holds the teacher's data, all on `TenantModel`. It is served at `/api/classroom/` only to the `TEACHER` of a workspace with `School.kind = individual`. Real schools keep their own modules.
- `apps/classroom/entitlements.py` is the single source of plan rules:

  | | Free trial | Teacher | Teacher Pro |
  |---|---|---|---|
  | Classes | 2 | 5 | No limit |
  | Students | 30 | 100 | No limit |
  | Lesson plans | 10 | No limit | No limit |
  | PowerPoint downloads | 3, with a small mark | No limit | No limit |
  | AI lesson plans a month | 0 | 0 | 50 |
  | Report cards, parent messages | No | No | Yes |

- The backend enforces every rule. Limits are checked while holding a lock on the workspace row, so parallel requests can't pass them.
- When no subscription covers today, the workspace is read-only. The teacher can read their work and ask for a plan. This doesn't wait for the nightly expiry job.
- Reminder emails go out two days before the end, on the last day, and when the trial has ended.
- A teacher asks for a plan in the app. The Super Admin activates it at `/platform/teachers` after payment is arranged outside the system, and can also extend a trial.
- PowerPoint files are built with `python-pptx` behind `apps/integrations/slides/`.
- AI lesson plans use the existing OpenAI key behind `apps/integrations/ai/lesson_provider.py`. Only the topic, subject, grade and language are sent, never student data.

## Consequences
- Lists use annotations and subqueries, and bulk saves use upserts, so the number of queries doesn't grow with the size of a class.
- Students have no login. Parents are reached by email only.
- Data is not deleted automatically after a trial ends. That needs the client's decision on the retention period.
- There is no online payment yet.
- AI lesson plans send the topic to OpenAI, outside Saudi Arabia. The client should confirm this before launch, because [ADR-0016](0016-interim-hosted-ai-api.md) names Groq or Gemini.
