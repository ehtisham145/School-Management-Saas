You are building the frontend of Lesson Lab, a bilingual (English and Arabic) school management system for private schools in Saudi Arabia.

## Source of truth
`index.html` and the `assets` folder in this project are the approved design demo. Read the whole file before writing any code. Its visual language is approved; do not redesign it.

Rules:
- Rebuild the home page as real components, matching the demo's layout, spacing, colors, type and copy.
- Reuse the demo's CSS values and copy. Do not paste the demo in as one large file.
- Replace the demo's JavaScript translation approach with a proper i18n setup.
- Extend the same design language to the app screens. Do not introduce a second visual style.

## Stack
Use the stack already in this repository. If the repository is empty, use Next.js (App Router), TypeScript and Tailwind CSS. Tell me which one you chose.

## Design tokens
Define these once as CSS variables or in the Tailwind theme. Never hard-code hex values in components.

| Token | Value | Use |
|---|---|---|
| navy | #1e3a5f | Primary buttons, links, icons |
| navy-hover | #172d4a | Primary button hover |
| navy-deep | #0f1d31 | Headings, trust strip, call-to-action box, footer |
| navy-soft | #e1eaf3 | Icon tiles, soft fills |
| navy-line | #c3d4e6 | Outline button borders, hover borders |
| orange | #F5781E | Accent fills, step numbers, focus ring |
| orange-hover | #FF8C3A | Orange button hover |
| orange-text | #B9500C | Orange text on white |
| orange-soft | #FEF0E5 | Soft orange fills |
| on-orange | #2A1400 | Text on orange |
| bg | #FFFFFF | Page and cards |
| bg-tint | #f8fafc | Alternating sections |
| ink | #0f172a | Main text |
| ink-soft | #475569 | Secondary text |
| line | #e2e8f0 | Card and header borders |
| on-dark | #FFFFFF | Main text on navy-deep |
| on-dark-soft | #c3d4e6 | Secondary text on navy-deep |

Color rules:
- Use mostly white and neutral surfaces, navy as the main color, and orange only as a small accent.
- Never use the orange #F5781E for text on white, and never put white text on it.
- Do not add purple, indigo, teal or gold, and do not add new gradients.
- App status colors only: success = emerald, warning = amber, danger = red, info = sky. Always pair a status color with text or an icon.

Status mapping:
| Color | Attendance | Fees | Results |
|---|---|---|---|
| Emerald | Present | Paid | Pass |
| Amber | Late | Pending or partial | Under review |
| Red | Absent | Overdue | Fail |
| Sky | On leave | Scholarship | Result pending |
| Slate | Holiday | Not generated | Not attempted |

## Typography
- English: IBM Plex Sans. Arabic: IBM Plex Sans Arabic. Weights 400, 500, 600 and 700 only.
- Headings are 700 weight. Keep the demo's sizes, including `clamp()` for the h1 and h2.
- Letter-spacing is -0.02em on English headings and 0 on Arabic. Arabic heading line-height is 1.3.
- Use `tabular-nums` for numbers in tables and totals.

## Shape and spacing
- Radius: 16px for cards, 12px for buttons, 10px for small buttons and inputs, 22px for the call-to-action box.
- Buttons are at least 48px tall, or 42px for the small size.
- Page width is at most 1240px, with a 24px side gutter (16px on phones).
- Use the demo's breakpoints: 1040px and 620px.
- Use soft shadows on hover only, as in the demo. Use real card borders.

## Arabic and right-to-left: required from the first commit
- Set `lang` and `dir` on `<html>`, rendered on the server. Store the chosen language in a cookie so there is no flash of the wrong language on load.
- Use logical properties only: `ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`, `inset-inline-*`. Do not use physical left and right classes.
- Put every user-visible string in the translation files, English and Arabic, with type checks that fail when a key is missing. Include labels, placeholders, errors and aria-labels.
- Keep the demo's existing Arabic copy word for word.
- Numbers, codes, phone numbers and emails stay left to right inside Arabic text. Wrap user-entered names in `<bdi>`.
- Flip directional icons such as arrows in right-to-left. Do not flip other icons or the logo.
- The hero photo is mirrored in Arabic so the text and the people swap sides. Do not mirror any other image.

## Home page
Sections, in this order: sticky header, hero with photo and two status cards, trust strip, features, roles, how it works, call to action, footer, floating WhatsApp button.

- Render all text on the server so search engines can read it. Add page metadata in both languages.
- Use an optimized image component for `assets/hero.jpg` and `assets/logo.png`, with fixed dimensions to prevent layout shift.
- The language menu must support Tab, arrow keys and Escape, and return focus to its button on close.

## App screens (after the home page)
Roles: school admin, principal, teacher, student, parent. Each role sees only what it needs.

Modules: dashboard, attendance, exams and report cards, fees, timetable, announcements and messages, users and settings.

Saudi context:
- The school week is Sunday to Thursday.
- Show Hijri dates beside Gregorian dates.
- Arabic is a full interface language, not an add-on.

Every screen must have:
- Loading, empty and error states, with a Retry action on errors. Never show a blank screen.
- Live validation, with errors shown under the field.
- A disabled button with a spinner while saving.
- A confirmation step before any destructive action.
- A layout that works at 360px width with no horizontal page scroll. Wide tables scroll inside their own container.

Build a small shared component set first (Button, Input, Select, Card, Badge, Table, Modal, EmptyState) and use it on every screen.

Accessibility: visible keyboard focus, WCAG AA contrast, real labels on inputs, and support for `prefers-reduced-motion`.

## Do not invent anything
The demo makes these claims, and I have not yet confirmed them:
- Data hosted in Saudi Arabia
- Attendance in under a minute
- Hijri dates throughout
- Report cards in Arabic and English

Keep their wording, but list them in your summary so I can confirm them. Do not add new claims, customer numbers, testimonials, prices or logos.

Sign in and About have no destination yet. Ask me, or build a simple route for them and tell me.

If there is no backend yet, put all data behind a typed API layer with clearly labelled mock data, so it can be swapped later. Never pretend a mocked action really happened.

## How to work
1. First, read the demo and the repository. Give me a short plan listing the folder structure, the tokens file and the order of screens. Wait for my approval before writing code.
2. Build in this order: tokens and fonts, i18n and right-to-left, shared components, home page, app shell, then one module at a time.
3. Check each page in English and Arabic, at phone and desktop widths, against the demo.
4. After each stage, tell me what changed, what checks you ran (type check, lint, tests) and what you did not verify. Do not claim something works unless you checked it.
5. Do not commit or push unless I ask.
