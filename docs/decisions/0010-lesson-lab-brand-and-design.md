# ADR-0010: Lesson Lab brand and one design language

- **Status:** Accepted
- **Date:** 2026-11-03

## Context
The product was named Schoolify and the public site had its own colors and fonts, separate from the logged-in app. The owner approved a new name and a design demo (`design/index.html`).

## Decision
- The product is **Lesson Lab**. Contact emails are `info@lessonlab.me` and `support@lessonlab.me`.
- One design language for the whole product: navy with a small orange accent on white, IBM Plex Sans and IBM Plex Sans Arabic. Tokens live once, in `frontend/src/app/globals.css`, and the old `.marketing` theme is removed.
- The site has five pages: Home, About Us, LMS, Pricing, Contact. `/features` became `/lms`.
- The language is in the URL (`/en`, `/ar`) and remembered in the `NEXT_LOCALE` cookie, so `lang` and `dir` are rendered on the server with no flash.
- Translation keys are type checked, and a key missing from either language fails the build.

## Consequences
- Logged-in screens pick up the new colors through the shared tokens, but they still need their own layout work.
- Pricing shows sample prices, labelled as samples, until real prices are confirmed.
