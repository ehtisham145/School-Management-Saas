# ADR-0020: Manrope + Cormorant Garamond for Latin text; Arabic unchanged

- **Status:** Accepted
- **Date:** 2026-11-12
- **Supersedes:** the Latin-typeface part of [ADR-0010](0010-lesson-lab-brand-and-design.md)

## Context

ADR-0010 set one typeface, IBM Plex Sans (+ IBM Plex Sans Arabic), for body text and headings alike, everywhere. The owner felt the result read flat — no distinction between a heading and a paragraph beyond size and weight — and asked for the text style used on a reference site (rizwanstationers.com), which pairs a serif display face with a clean grotesk body face.

## Decision

- **Body text (Latin):** Manrope, replacing IBM Plex Sans. Loaded via `next/font/google`, CSS variable `--font-manrope`, mapped to the existing `--font-sans` token.
- **Headings (Latin, `h1`/`h2`/`h3`):** Cormorant Garamond, a new display face with no prior role in this project. Mapped through the existing (previously unused) `--font-heading` token, applied globally via the base `h1, h2, h3` rule rather than per-component classes, so every heading picks it up without hunting down each usage.
- **Arabic is unchanged:** IBM Plex Sans Arabic stays the body **and** heading face for `dir="rtl"` content. Cormorant Garamond has no Arabic glyphs, and no Arabic-appropriate companion to it was part of this request, so `html[dir="rtl"] h1/h2/h3` explicitly overrides back to IBM Plex Sans Arabic — without that override, Arabic headings would silently fall through to the browser's default serif instead of the project's chosen Arabic face.
- Heading weight dropped from 700 to 600 and the `-0.02em` letter-spacing was removed for Latin headings: both were tuned for a tight grotesk and fought the open, classical rhythm of a Garamond-style serif. Arabic headings keep weight 700, which still suits IBM Plex Sans Arabic.

## Consequences

- ✅ Real typographic hierarchy in English: a Garamond display face reads as considered/editorial, distinct from the body text, without touching every component that renders a heading.
- ✅ Swappable later the same way: change the two font-loading lines in `src/app/[locale]/layout.tsx` and the two token lines in `globals.css`; nothing else references a font name directly.
- ⚠️ Latin and Arabic headings now look visibly different in character (serif vs. the existing grotesk) on a page that switches language — a deliberate trade-off given no Arabic serif pairing was requested, not an oversight.
- ⚠️ Two more font families downloaded (Manrope, Cormorant Garamond) alongside IBM Plex Sans Arabic. All three are self-hosted through `next/font/google` (no runtime Google Fonts request), so this is a build-size/variety cost, not a page-load network cost.
