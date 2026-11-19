# ADR-0023: New Lesson Lab brand mark

- **Status:** Accepted
- **Date:** 2026-11-19
- **Supersedes:** the logo part of [ADR-0010](0010-lesson-lab-brand-and-design.md)

## Context
The old logo (an orange flask with bubbles on an open book, "Lesson Lab" in a rounded bold sans) had three problems:
- It had too much detail. The bubbles and the flask outline blurred at 38px, the logo's height in the phone header.
- It had no version for dark backgrounds, so the footer and the sidebar had to put it inside a white box.
- Its wordmark used a font the app doesn't use anywhere else.

The owner chose concept C from three options.

## Decision
- **Mark:** a navy open book with an orange flask rising from its spine. It is made of flat shapes on a 48 × 48 grid, with no gradients or thin lines, so it still reads at 16px.
- **Wordmark:** "Lesson" in navy, "Lab" in orange, set in Manrope 700 (the app's text font) and converted to outlines. The Arabic lockup "ليسون لاب" uses IBM Plex Sans Arabic 700. The icon is never mirrored in RTL.
- **Colors:** only the existing tokens: navy `#1E3A5F`, orange `#F5781E`, and white on navy-deep `#0F1D31`.
- **Masters:** SVG files live in `docs/design/assets/logo/`: horizontal, stacked, Arabic and icon-only lockups, each in four versions (`color`, `white`, `navy`, `mono-white`).
- **In the app:**
  - `public/brand/logo.webp` is the color lockup and `public/brand/logo-white.webp` the white one. Both are 1068 × 240 (2x for a 534 × 120 slot).
  - `<Logo variant="white" />` is used on navy-deep, so the footer and the platform sidebar no longer need a white box.
  - `src/app/icon.png` (512px) and `src/app/apple-icon.png` (180px, on a white tile) are the favicons.
  - The email logo `apps/integrations/email/assets/logo-on-dark.png` is the white lockup. `BRAND_LOGO_WIDTH` is now 160, for the new 4.45:1 ratio.
- **Usage rules:**
  - Keep clear space equal to the flask height on all sides.
  - Minimum size is 24px tall for the lockup and 16px for the icon.
  - Don't stretch the logo, recolor it, put it on orange, or mirror it.

## Consequences
- ✅ One simple mark that works in the header, in the footer, in emails and as a favicon.
- ✅ Dark backgrounds use the white version directly, with no extra box.
- ⚠️ The welcome screen after sign-in still shows the color logo on its white chip. This is on purpose, because its light-sweep animation is drawn over that chip.
- ⚠️ If `BRAND_LOGO_URL` points to a hosted logo, that file has to be replaced by hand with the new white lockup.
