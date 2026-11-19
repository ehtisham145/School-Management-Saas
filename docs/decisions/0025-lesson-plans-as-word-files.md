# ADR-0025: Lesson plans as Word files with python-docx

- **Status:** Accepted
- **Date:** 2026-11-19

## Context
Teachers download a lesson plan as PowerPoint to teach from. Many also keep a written lesson plan, often printed or handed to a supervisor, and edit it in Word. They asked for a Word download next to PowerPoint.

## Decision
- `GET /api/classroom/lesson-plans/{id}/document/` returns the lesson plan as a `.docx` file, with the title, subject, grade, class, date and every section that has text.
- The file is built with **python-docx** behind `apps/integrations/word/`, the same way python-pptx sits behind `apps/integrations/slides/`. It is imported only inside the view, so the rest of the API still runs without it.
- An Arabic lesson plan gets right-to-left paragraphs and Arabic font settings.
- Word downloads are not counted against any limit. On the trial, and after it ends, the footer says "Made with Lesson Lab", as on the PowerPoint slides.

## Consequences
- One more library to install: `python-docx` in `requirements/base.txt`.
- The PowerPoint limit stays the trial's reason to upgrade; a Word file has no slides, so it doesn't replace it.
