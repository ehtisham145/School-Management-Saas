# ADR-0003: Authentication with session cookies; membership-based RBAC

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Six roles (Super Admin, School Admin, Principal, Teacher, Student, Parent). Login differs by role: parents by email OTP (SMS/WhatsApp rejected for cost), students by school-issued username, staff by email + password + 2FA. No SSO. The only client is the browser (web + PWA).

## Decision
- **Django session authentication** with `HttpOnly; Secure; SameSite=Lax` cookies. Frontend and API are served from the same origin (Caddy routes `/api`, `/ws`), so there is no CORS and no JWT.
- Login methods: email + password; system-generated, school-prefixed username + password; email OTP (hashed, 10-min, single use, rate-limited); TOTP 2FA via `django-otp` (mandatory for Super Admin and School Admin).
- Argon2 hashing, `django-axes` lockout, DRF throttling.
- Authorization: `Membership(user, school, role)` plus a central permission matrix (`can(role, action)`) and row scoping in selectors (teacher → assigned sections; parent → linked children). A user can hold memberships in several schools.
- Super Admin is a platform flag, not a membership.

## Consequences
- ✅ Tokens can't be stolen through XSS; instant logout and revocation; CSRF handled by Django.
- ✅ Adding a login method later (SMS, SSO) is an extra backend, not a redesign.
- ⚠️ A future native mobile app would need token auth → add DRF token/JWT endpoints at that point.
- ⚠️ Email OTP depends on deliverability → SPF/DKIM/DMARC configured; username fallback for parents without email.
