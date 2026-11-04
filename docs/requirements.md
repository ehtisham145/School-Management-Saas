# Requirements

_Last updated: 2026-11-03. Source: discovery interview with the developer; client details still to confirm are marked **(TBC)**._

## 1. Product

A School Management System sold as **multi-tenant SaaS** to private schools in **Saudi Arabia**.
The platform owner (Super Admin) onboards schools; each school manages its own staff, students and parents independently.

## 2. Users and roles

| Role | Scope | Main capabilities |
|---|---|---|
| **Super Admin** | Whole platform | Register schools, create school admin accounts, plans/subscriptions, quotations, demo requests |
| **School Admin** | One school | Manage users, classes, fees, school settings |
| **Principal** | One school | Track everything in the school: teachers, students, attendance, results (mostly read + approve) |
| **Teacher** | Assigned sections/subjects | Attendance, marks, homework, messages with parents of their students |
| **Student** | Self | Timetable, homework, results, announcements |
| **Parent** | Own children only | Attendance, results, homework, fees, announcements, messaging with teachers |

A person can hold roles in more than one school (e.g. a parent with children in two schools) — one login, a school switcher.

## 3. Features

### MVP (Phase 1 — 4 weeks)
- Multi-tenancy + Super Admin: create school, create its admin, activate and deactivate schools, follow up demo requests
- Auth: username/password, email code, and 2FA. 2FA is mandatory for Super Admins and School Admins. New School Admins get no password: they sign in with an email code, then set up 2FA
- Role-based access for the 6 roles above
- Academics: academic years, terms, grades, sections, subjects, teacher assignment, enrollment
- Timetable
- Daily attendance + parent notification
- Exams, marks entry, report card PDF
- Homework/assignments with file upload and student submission
- Fees: fee structures, dues, **manual (cash) payment recording**, receipts PDF
- Announcements, teacher–parent messaging, live (no-refresh) in-app notifications
- Arabic + English with full RTL; Hijri + Gregorian date display
- Audit log of sensitive changes (marks, attendance, fees, users)
- Lesson plans + presentations: **manual editor and AI generation** (Teachy-like)
- Online classes

### Phase 1.5 (weeks 5–8)
- Super Admin: quotation builder → PDF → email to school's business email
- Subscription plans (monthly/yearly — **TBC with client**), manual activation/expiry
- Public website with five pages: Home, About Us, LMS, Pricing, Contact (Arabic/English, SEO). Book a demo and Contact forms are saved and emailed to the team
- PWA (installable, web push notifications)

### Phase 3 (later)
- Online fee payments (Mada, Apple Pay, STC Pay) — only if client asks
- Further client-requested features

### Out of scope
- Transport module
- Native mobile apps (PWA covers phones)
- SSO (Google/Microsoft)
- SMS/WhatsApp (cost) — all OTP and alerts go by email + in-app + push

## 4. Scale assumptions

Average Saudi private school assumed: **~800 students → ~2,000 accounts** (students, ~1.5 parents each, ~50 staff).

| Point | Schools | Accounts |
|---|---|---|
| Launch | 1–2 | 2K–4K |
| Year 1 | ~10 | ~20K |
| Year 3 | ~50 | ~100K |

Traffic: peaks during school hours (07:00–14:00 KSA), spikes at morning attendance and on result days; quiet at night (deploy/maintenance window).

## 5. Non-functional requirements

| Area | Requirement |
|---|---|
| Data residency | **All data hosted in Saudi Arabia** (latency + PDPL) |
| Compliance | Saudi **PDPL**; children's data treated as sensitive |
| Availability | ~99.5%, no planned downtime in school hours |
| Backups | Daily automated DB + file backups, kept in KSA, 30-day retention, restore tested monthly |
| Audit | Who changed what and when, for marks/attendance/fees/users |
| Languages | Arabic (RTL) and English, per-user preference |
| Budget | **~$20/month** infrastructure at launch |
| Team | 1 developer (Django/FastAPI, Next.js, Docker, VPS) + AI coding agent |
| Timeline | Client wants it in ~1 month → MVP in 4 weeks, SaaS layer in month 2 |

## 6. Open questions for the client (TBC)
- Subscription billing: monthly, yearly or both; pricing tiers
- Pricing: the site shows **sample** plans and prices (Basic SAR 1,500, Premium SAR 3,000, Advanced SAR 5,000 per month). Confirm the real ones
- Do any parents lack email? (fallback: school-issued username/password for parents)
- Fee structure specifics: installments, discounts, sibling discounts, VAT on receipts?
- Report card format — does the client have a template (Ministry of Education format)?
- Grading scheme(s) used by target schools

## 7. Website claims to confirm before going public
The site says these, and they are not yet true or not yet confirmed:
- Data hosted in Saudi Arabia (no server has been bought yet)
- Attendance in under a minute, Hijri dates throughout, report cards in Arabic and English
- Modules described as working: attendance, exams, fees, timetable, messaging (not built yet)
- About: "working directly with a small number of pilot schools"
- Contact: "usually a reply the same day". Pricing FAQ: a full data export when a school leaves
- Pricing intro says schools are quoted per school, which doesn't match a fixed price list
