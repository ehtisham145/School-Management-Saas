# ADR-0027: The teacher app shows only the AI tools; classes move to the school plan

- **Status:** Accepted
- **Date:** 2026-11-26
- **Amends:** [ADR-0022](0022-teacher-classroom-app.md), [ADR-0024](0024-ai-lesson-plans-on-every-teacher-plan.md)

## Context
A teacher tried the individual app and found it hard to use after signing in, most of all on a phone. The menu had six items, the overview counted classes, students and attendance, and the forms asked for a class. Teachers buy the app for the AI tools: lesson plans, slides and tests. Classes, students, attendance, marks, report cards and parent messages are what a whole school needs, and the school product covers them.

## Decision
- **Classes are off for individual teachers.** `TEACHER_CLASSES_ENABLED = False` in settings, read through `WorkspaceAccess.classes_enabled`. It covers classes, students, attendance, marks, the gradebook, report cards and parent messages. Their endpoints answer 403 `school_plan_only`; `GET /api/classroom/workspace/` returns `features.classes` so the app hides them.
- **No data is deleted.** Classes, students and marks that teachers saved stay in the database. Turning the setting on brings them back as they were. The code and its tests stay; the tests run with the setting on, and `test_teacher_app.py` checks it off.
- **The menu is Home, Lesson plans, PowerPoint presentations, Virtual tests, Paper design, My plan.** On phones it is a bar at the bottom of the screen. Old links to Classes or Parent messages show a note that they are part of the school plan.
- **Home** has three large ways in ("Make a lesson plan with AI", "Make a PowerPoint with AI", "Make a Digital / Virtual Test with AI"), recent lesson plans and tests, and the AI allowance.
- **PowerPoint is its own page**, "Make a PowerPoint presentation with AI". It is built on lesson plans: the teacher gives a topic, reviews the AI lesson, and the slides download as soon as it is saved. It uses the AI lesson plan allowance and, on the trial, the PowerPoint download limit. A separate AI slide generator was not built: it would need its own provider call, allowance and tests for the same result.
- **Branding on files.** Every slide has a "Lesson Lab" footer with the teacher's name and the slide number; the title slide says "Prepared by {teacher}". The Word lesson plan lists the teacher and has a "Lesson Lab" footer. Trial files keep "Made with Lesson Lab". The teacher's name doesn't decide a file's language.
- **Paper design is its own page** in the side menu (not on phones' bottom bar). One `PaperDesign` per workspace holds the color, text size, columns and name line; `GET`/`PUT /api/classroom/paper-design/` read and save it. Every test paper and answer key uses it when downloaded, including tests made before, and a new test without a theme of its own takes it. The test editor links to it instead of showing the design.
- **Plan limits are unchanged.** The pricing text for Teacher and Teacher Pro now lists only what the app has.

## Consequences
- ✅ Fewer screens and one clear job per page; the menu fits a phone's bottom bar.
- ⚠️ Teacher Pro loses report cards and parent messages; what is left above Teacher is the larger AI allowance. Revisit Pro's price or extras with the client.
- ⚠️ Teachers who already saved classes can't see them while the setting is off. Tell them before release, or export their data on request.
- The Super Admin's teacher list still counts classes and students from the database.
