# ADR-0006: Bilingual Arabic/English with RTL from day one

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Saudi users expect Arabic first; some staff prefer English. Retrofitting RTL later means touching every screen.

## Decision
- Frontend: `next-intl`, locale-prefixed routes `/ar/...`, `/en/...`; `<html lang dir>` set per locale; default locale **English** (changed 2026-10-30 at the developer's request); first-time visitors are redirected by their browser's `Accept-Language`, so Arabic browsers still land on `/ar`. User preference stored on the profile.
- Styling: Tailwind **logical utilities only** (`ms-`, `me-`, `ps-`, `pe-`, `start-`, `end-`, `text-start`). `left`/`right` classes are banned in review. Icons that imply direction are flipped with `rtl:` variants.
- Fonts: an Arabic-capable family (e.g. IBM Plex Sans Arabic / Noto Naskh Arabic), also used in PDFs.
- UI strings in `messages/ar.json` and `messages/en.json`; no hard-coded text in components.
- Backend: Django i18n for emails, PDFs and API error messages (driven by `Accept-Language` / user preference).
- User-entered master data that needs both languages (subjects, grades, fee heads, school name) has `*_ar` and `*_en` fields. Free text (announcements, messages) is stored as entered.

## Consequences
- ✅ Arabic is first-class; there is no second pass later.
- ⚠️ Every screen must be checked in both directions → add both locales to the manual QA checklist.
