# Security & Compliance Essentials

This system stores **children's personal data** for multiple organisations. A cross-school leak or a breach would end the business. These rules are non-negotiable, even under deadline.

## 1. Tenant isolation
- [ ] Every tenant model inherits `TenantModel`; every read goes through a school-scoped selector.
- [ ] `request.school` comes from the server-side session membership only.
- [ ] FKs in request bodies are validated to belong to `request.school`.
- [ ] Every endpoint has a cross-tenant test (expects 404).
- [ ] Celery tasks re-load objects by `(school_id, id)`, never by `id` alone.
- [ ] Hardening phase: PostgreSQL Row-Level Security as a second layer.

## 2. Authentication
- [ ] Argon2 password hashing; Django password validators on.
- [ ] `django-axes`: lock after 5 failed attempts (per user + IP), with cool-off.
- [ ] Email OTP: random 6 digits, stored **hashed**, 10-min expiry, single use, 5 attempts max, resend throttled (e.g. 1/min, 5/hour).
- [x] TOTP 2FA mandatory for Super Admin and School Admin.
- [ ] Recovery codes issued once (today a lost device is reset by an email code alone).
- [ ] Session cookies `HttpOnly; Secure; SameSite=Lax`; session rotated on login and on privilege change; logout invalidates server-side.
- [ ] Login and OTP endpoints return identical responses for "user not found" and "wrong password".

## 3. Authorization
- [ ] Backend enforces every permission; UI hiding is cosmetic only.
- [x] Default deny on `TenantScopedViewSet`: an action without a policy fails closed.
- [ ] Default deny for every other endpoint (plain `APIView`s only require login by default).
- [ ] Django admin requires 2FA or is restricted (`/admin` accepts a password alone; `/api/platform/` already refuses such a session).
- [ ] Parents see only linked children; teachers only assigned sections (current year).
- [ ] Super Admin cross-school actions are audit-logged.

## 4. Web security
- [ ] HTTPS only (Caddy), HSTS on.
- [ ] Headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `frame-ancestors 'none'`.
- [ ] CSRF protection on all state-changing requests.
- [x] DRF throttling on auth, OTP and demo-request/contact endpoints.
- [ ] DRF throttling on file-upload endpoints.
- [ ] Behind Caddy, configure DRF `NUM_PROXIES` so throttling uses the real client IP and `X-Forwarded-For` can't be spoofed.
- [ ] Decide how long demo requests and contact messages are kept (they hold personal data).
- [ ] No raw SQL with string formatting; ORM or parameterised queries only.
- [ ] User-generated HTML (announcements, lesson plans) sanitised server-side (`nh3`) before storing or rendering.
- [ ] `DEBUG=False`, Django admin on a non-default path, restricted to platform admins + 2FA.

## 5. Files
- [ ] Private bucket; access only via short-lived presigned URLs after a permission check.
- [ ] Allow-list of MIME types and extensions, verified from file content, not just the name; size limit.
- [ ] Storage keys are random UUIDs under `school/<id>/`; original names kept only as metadata.
- [ ] Later: ClamAV scan in a Celery task before files become downloadable.

## 6. Data protection (Saudi PDPL)
- [ ] All primary data and backups stored **in KSA** (OCI Riyadh + Jeddah).
- [ ] Role split: **school = data controller, platform = data processor**. Sign a data processing agreement with every school.
- [ ] Privacy policy (Arabic + English) on the marketing site; parental consent captured by the school for student data.
- [ ] Data minimisation: no national ID / Iqama numbers unless a feature truly needs them; if stored, encrypt the field.
- [ ] Out-of-KSA services (Sentry, SES) receive no student PII: `send_default_pii=False`, scrub request bodies; emails carry minimal data + a link into the app.
- [ ] Retention: define how long data is kept after a school leaves; provide export + deletion on request.
- [ ] Breach procedure documented: who is notified, how fast. The PDPL implementing regulations set a short deadline for notifying SDAIA (72 hours — **confirm with a Saudi legal advisor**).
- [ ] Get a short legal review of the DPA and privacy policy before the first paying school.

## 7. Audit logging
- [ ] `django-auditlog` on marks, attendance, fees/payments, users/memberships, school settings.
- [ ] Each entry stores actor, school, IP, timestamp, before/after.
- [ ] Audit log is append-only for app users; visible to Principal/School Admin for their school.
- [ ] Also log security events: logins, failed logins, OTP failures, 2FA changes, password resets, role changes.

## 8. Infrastructure
- [ ] SSH key-only, root login disabled, non-standard user, `fail2ban`; ideally SSH reachable only from your IP (OCI security list).
- [ ] Only ports 80/443 open publicly; Postgres and Redis bound to the Docker network only.
- [ ] Unattended security upgrades on the VM; monthly image rebuilds for base-image patches.
- [ ] Secrets in `.env` (chmod 600) and GitHub secrets; never committed. Rotate if leaked.
- [ ] Backups encrypted (e.g. `age`/`gpg`) before upload; **restore test monthly**.
- [ ] Dependency scanning: Dependabot + `pip-audit` + `npm audit` in CI.

## 9. Before go-live checklist
- [ ] Cross-tenant tests green for all endpoints
- [ ] Manual test with two schools and every role
- [ ] `python manage.py check --deploy` clean
- [ ] Backup → restore performed end-to-end at least once
- [ ] Sentry receives an error with no PII in it
- [ ] Uptime monitor alerts reach your phone
