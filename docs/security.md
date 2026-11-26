# Security & Compliance Essentials

This system stores **children's personal data** for multiple organisations. A cross-school leak or a breach would end the business. These rules are non-negotiable, even under deadline.

## 1. Tenant isolation
- [x] Every tenant model inherits `TenantModel`; every read goes through a school-scoped selector.
- [x] `request.school` comes from the server-side session membership only.
- [ ] FKs in request bodies are validated to belong to `request.school`.
- [x] Every tenant endpoint has a cross-tenant test (expects 404).
- [ ] Celery tasks re-load objects by `(school_id, id)`, never by `id` alone.
- [ ] Hardening phase: PostgreSQL Row-Level Security as a second layer.

## 2. Authentication
- [x] Argon2 password hashing; Django password validators on.
- [x] Staff created without a password (a new School Admin) sign in once with an email code and must set a password before using the app. The set-password endpoint works only while the account has no password, runs the password validators, and keeps the current session.
- [x] Teacher sign-up: no account exists until the email is proven with a hashed 6-digit code (10-minute expiry, 5 attempts, one email every 30 seconds, `teacher_signup` throttle of 10 an hour per IP, honeypot). At most 3 trials can start from one IP address in 24 hours ([ADR-0024](decisions/0024-ai-lesson-plans-on-every-teacher-plan.md)). The password is never stored before that, and a registered email gets the same response ([ADR-0021](decisions/0021-individual-teacher-workspace-and-trial.md)).
- [x] The teacher's classroom API is limited to the teacher of an individual workspace. Every read is scoped to that workspace, another teacher's records answer 404, and plan limits and read-only mode are enforced on the backend ([ADR-0022](decisions/0022-teacher-classroom-app.md)).
- [x] AI lesson plans send only the topic, subject, grade and language to the provider, never student data.
- [x] AI tests ([ADR-0026](decisions/0026-ai-tests-from-pdf.md)): an uploaded PDF is checked for the PDF signature, 8 MB and 50 pages, and is never stored. Only its page text is kept, per workspace, and deleted after a day. Only the chosen pages' text, subject, grade and language go to the provider; the upload screen asks teachers not to upload student names or marks. The prompt treats the PDF's text as material only and ignores instructions inside it, and every question must quote the PDF to be kept. Uploads and AI calls are throttled (`exam_upload`, `exam_ai`) and AI tests have a per-plan allowance.
- [x] Caddy sends a Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff`, a referrer policy and a permissions policy on every response. Scripts still allow `'unsafe-inline'` because Next.js needs it without nonces.
- [ ] CI fails on high or critical npm advisories in production packages. One exception runs until 2026-12-18: the picomatch ReDoS (GHSA-fc5q-39xc-vjpf), which has no fixed version yet and needs an attacker-supplied glob pattern (`.github/scripts/audit-npm.mjs`). Remove it when a fix is published.
- [ ] Before individual teachers go live: production in Saudi Arabia, a reviewed privacy policy and Terms of Service. Staging holds test data only.
- [x] `django-axes`: lock after 15 failed attempts (per user + IP), with a 1-hour cool-off.
- [x] Emails: anything a user typed, including names, goes through `user_text()` before it is placed in email markup. Codes and links are never logged, and a code is never in a subject or preheader.
- [ ] Email OTP: random 6 digits, stored **hashed**, 10-min expiry, single use, 5 attempts max, resend throttled (e.g. 1/min, 5/hour).
- [ ] No two-factor authentication: it was removed at the owner's request ([ADR-0018](decisions/0018-remove-two-factor-authentication.md)). A password or an email code alone signs in every role, including Super Admin. Revisit before real school data goes live.
- [x] Session cookies are `HttpOnly; SameSite=Lax`, and `Secure` on servers. A session ends 12 hours after sign-in.
- [ ] Session rotated on privilege change; logout invalidates server-side.
- [x] Login and OTP endpoints return identical responses for "user not found" and "wrong password".
- [x] Public sign-in and lead form endpoints use no session, so an old session can't block them. Their protection is throttling, and sign-in, teacher sign-up and password reset also refuse a browser request from another website (`TrustedOrigin`). Endpoints for signed-in users still require CSRF.
- [ ] Tighter email code resend limit: today it is only the shared `email_code` throttle (50/min), not the 1/min and 5/hour above.

## 3. Authorization
- [ ] Backend enforces every permission; UI hiding is cosmetic only.
- [x] Default deny on `TenantScopedViewSet`: an action without a policy fails closed.
- [ ] Default deny for every other endpoint (plain `APIView`s only require login by default).
- [ ] Django admin is restricted (`/admin` accepts a password alone).
- [ ] Parents see only linked children; teachers only assigned sections (current year).
- [x] Super Admin cross-school actions are audit-logged in `AuditEvent` with actor, IP and time: schools, demo requests, plans, subscriptions and quotations ([ADR-0019](decisions/0019-platform-audit-log-and-quotation-pdfs.md)). The log is read-only in the API and in Django admin.
- [x] Plans, subscriptions, quotations, usage and the audit log need a platform admin session; school roles get 403.
- [x] A deactivated school loses tenant access at once, including for users already signed in, and can't be switched into.
- [x] Reading and updating demo requests needs a platform admin session. The public form stays write-only and can't set the status or notes.

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
- [ ] `DEBUG=False`, Django admin on a non-default path, restricted to platform admins.

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
- [ ] Each entry stores actor, school, IP, timestamp, before/after. Done for platform actions (`AuditEvent`); tenant data still to do.
- [ ] Audit log is append-only for app users; visible to Principal/School Admin for their school.
- [ ] Also log security events: logins, failed logins, OTP failures, password resets, role changes.
- [x] The client IP comes from `REMOTE_ADDR` locally and from `X-Forwarded-For` only in production (`TRUST_X_FORWARDED_FOR`), where Caddy sets that header itself.
- [x] Quotation PDFs escape everything people typed (Django template autoescaping); quotation emails send only the name, number, total and date, with the PDF attached.

## 8. Infrastructure
- [ ] SSH key-only, root login disabled, non-standard user, `fail2ban`; ideally SSH reachable only from your IP (OCI security list).
- [ ] Only ports 80/443 open publicly; Postgres and Redis bound to the Docker network only.
- [ ] Unattended security upgrades on the VM; monthly image rebuilds for base-image patches.
- [ ] Secrets in `.env` (chmod 600) and GitHub secrets; never committed. Rotate if leaked. SMTP passwords stay in `.env` only, on every machine.
- [ ] Backups encrypted (e.g. `age`/`gpg`) before upload; **restore test monthly**.
- [x] Dependency scanning: Dependabot + `pip-audit` + `npm audit` in CI.
- [x] Staging auto-deploy uses a `deploy` user whose CI key can only run `staging/deploy.sh` (forced command + `restrict`), the script accepts only a commit SHA, and the registry token is short-lived and never stored on the server ([ADR-0013](decisions/0013-staging-auto-deploy.md)). GitHub-hosted runners have changing IPs, so SSH can't be limited to one IP while deploys come from them.

## 9. Before go-live checklist
- [ ] Cross-tenant tests green for all endpoints
- [ ] Manual test with two schools and every role
- [ ] `python manage.py check --deploy` clean
- [ ] Backup → restore performed end-to-end at least once
- [ ] Sentry receives an error with no PII in it
- [ ] Uptime monitor alerts reach your phone
