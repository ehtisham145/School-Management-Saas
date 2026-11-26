# ADR-0026: AI tests made from a teacher's PDF

- **Status:** Accepted
- **Date:** 2026-11-26

## Context
Teachers want to turn a chapter, notes or a worksheet into a printed test without writing every question. The plan is to read a PDF, let the AI write questions in a pattern the teacher chooses, and print the test with an answer key. An AI can write questions that sound right but aren't in the material, so the teacher must check every question before it is saved. This first phase is a printed test only. Students have no accounts yet, so an online test comes later.

## Decision
- **Flow.** The teacher uploads a PDF (`POST /api/classroom/exam-sources/`), chooses pages and a pattern, and starts a draft (`POST /api/classroom/exam-drafts/`). A Celery task on the new `ai` queue writes it, and the app asks for it every 2 seconds (`GET /exam-drafts/{id}/`). The teacher reviews and edits it, then saves it as a test (`POST /exams/`). `GET /exams/{id}/download/?type=pdf|docx&answers=true` gives the paper or its answer key.
- **PDF text with pypdf**, behind `apps/integrations/pdf/text_extractor.py`. The upload is checked for the PDF signature, size (8 MB, under Caddy's 10 MB request limit) and pages (50). Locked, broken and scanned PDFs are refused with their own error code. Page numbers and running headers are removed. **The file itself is never stored.** Only the text of each page is kept, in `SourceDocument`, for one day. The same file uploaded again in that day is matched by its SHA-256 and not read again.
- **Patterns.** Three ready patterns are in code (`apps/classroom/exams.py`). A teacher can save up to 30 of their own (`ExamPattern`). A pattern is up to 6 sections of question kind (multiple choice, true or false, fill in the blank, short answer), count (1 to 30), marks each and level. An AI test has up to 50 questions; a saved test up to 100.
- **How the AI writes** (`apps/integrations/ai/exam_provider.py`, `gpt-4o-mini`, strict JSON schema):
  1. One short call lists the key topics of the chosen pages.
  2. One call per section, with that section's share of the topics, so the whole chapter is covered. The calls run side by side in a thread pool inside the task. Not a Celery group: that needs a result backend, and the calls only wait on the network.
  3. Every question is checked in `exams.build_questions()`: shape and length, 3 to 6 different choices with a real right answer, no "all of the above", true or false only, exactly one blank, and no repeats.
  4. **Source check.** Each question comes with a quote copied from the material. The backend looks for it in the PDF's text, ignoring case, punctuation and Arabic marks, and allowing a word or two to differ. A question whose quote isn't found is dropped, and the quote's page is shown to the teacher.
- **Allowance.** AI tests have their own allowance next to AI lesson plans (`ai_exams`: trial 5, Teacher 20 a month, Teacher Pro 60 a month), counted with `AIGeneration.kind = "exam"`. A draft being written holds a place, so many at once can't pass the limit. A draft that fails, or ends with no good question, isn't counted. The `exam_ai` throttle (20 an hour) and `exam_upload` throttle (30 an hour) also apply. Writing one question again is limited to 5 per draft and isn't counted.
- **Drafts last one day.** A Celery beat task each hour marks drafts stuck for 15 minutes as failed and deletes drafts and PDF text older than a day.
- **Paper.** `apps/classroom/exam_documents.build_paper()` works out every line once (numbering, choice letters, marks, labels), and the PDF (WeasyPrint) and Word (python-docx, `apps/integrations/word/exam_document.py`) only lay it out. Seven print colors, three text sizes, one or two columns, and an optional name and number line. Arabic tests are right to left with Arabic letters for the choices. Trial papers carry "Made with Lesson Lab".

## Consequences
- ✅ Teachers get a checked draft in under a minute, and nothing is saved without their review.
- ✅ No uploaded file sits on our servers; the text is gone after a day.
- ⚠️ One more library: `pypdf` in `requirements/base.txt`.
- ⚠️ The worker must read the `ai` queue (`-Q emails,ai,celery`). Staging's compose file does.
- ⚠️ The chosen pages' text goes to the AI provider, as lesson content does under [ADR-0016](0016-interim-hosted-ai-api.md). The upload screen asks teachers not to upload files with student names or marks. This still needs the client conversation ADR-0016 asks for.
- ⚠️ Scanned PDFs need OCR, and Arabic OCR is hard. They are refused for now.
- Later phases: online tests students take with a link and code, marks into the gradebook, OCR, a question bank.
