# ADR-0005: Store dates in Gregorian/UTC, display Hijri (Umm al-Qura)

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Saudi schools use both Hijri and Gregorian dates on screens, report cards and receipts. The academic calendar is Gregorian (Ministry of Education), while many users expect Hijri alongside.

## Decision
- The database stores `date` (Gregorian) and `timestamptz` (UTC) only. **Hijri is never stored.**
- Display timezone: `Asia/Riyadh`.
- Frontend: `Intl.DateTimeFormat(locale, { calendar: 'islamic-umalqura' })`. A per-user/school setting picks Hijri, Gregorian or both.
- Backend/PDFs: `hijridate` (Umm al-Qura) for conversion in templates.
- Date pickers input Gregorian; show the Hijri equivalent next to them.

## Consequences
- ✅ Sorting, ranges, reports and arithmetic stay simple and correct.
- ✅ One conversion source per side, matching the official Saudi calendar.
- ⚠️ Hijri input (typing a Hijri date) is not supported in MVP — add a Hijri picker later if users ask.
