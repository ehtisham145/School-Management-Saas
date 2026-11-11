# ADR-0019: Own audit log for Super Admin actions; quotation PDFs with WeasyPrint

- **Status:** Accepted
- **Date:** 2026-11-11

## Context
The Super Admin panel now manages plans, subscriptions and quotations, on top of schools and demo requests. [security.md](../security.md) requires cross-school actions to be audit-logged, and until now they went only to the application log. [tech-stack.md](../tech-stack.md) named `django-auditlog` for audit logging.

Quotations must reach a school as a PDF, in English or Arabic, with Saudi VAT. Tech-stack already chose WeasyPrint for PDFs but nothing used it yet.

## Decision
- **Audit log:** a small `apps/audit` app with one model, `AuditEvent` (actor, actor label, action, target type/id/label, school, IP, details JSON, time). Services call `record_event()` inside the same transaction as the change, so an entry exists exactly when the change does; it refuses to run outside a transaction. Actions are a fixed list (`school.created`, `quotation.sent`, ...). Scheduled jobs record with no actor ("System").
  - Why not `django-auditlog` here: it records field diffs of models, while the panel needs business actions ("quotation sent to X", "subscription expired because it ended") with the request IP. `django-auditlog` stays the plan for field-level history of tenant data (marks, attendance, fees).
  - The IP is `REMOTE_ADDR` locally and the first `X-Forwarded-For` address in production (`TRUST_X_FORWARDED_FOR`), because Caddy replaces that header with the real client address.
  - The log is read-only: a list endpoint only, and Django admin can't add, change or delete entries.
- **PDFs:** WeasyPrint behind `apps/integrations/pdf/renderer.py` (`html_to_pdf`), imported lazily so the app still starts where Pango is missing. The quotation is a Django template (`templates/pdf/quotation.html`) with English and Arabic labels side by side in `apps/platform/documents.py`, RTL for Arabic and Umm al-Qura dates from `hijridate` ([ADR-0005](0005-dates-gregorian-storage-hijri-display.md)). The PDF is built in a Celery task when the quotation is sent and emailed as an attachment; the panel can also download it.
- The backend image installs `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0` and `fonts-dejavu-core`. CI installs the same packages, sets `REQUIRE_PDF=1` so the real-PDF test can't be skipped, and checks the image makes a PDF on a read-only filesystem.

## Consequences
- Every Super Admin change is visible in the panel with who, when and from where.
- Two audit mechanisms will exist once tenant auditing starts. They answer different questions (actions vs field history), and each is used for its own data.
- The backend image grows by the Pango and font packages (roughly 30–40 MB).
- PDFs use DejaVu Sans, which covers Arabic but isn't the brand font. Bundling IBM Plex Sans Arabic is a follow-up.
- On Windows without GTK, PDFs can't be made locally: the download answers 503 `pdf_unavailable`, and the real-PDF test is skipped there.
- Quotation emails are still in English only, like the other emails; the PDF itself follows the chosen language.
