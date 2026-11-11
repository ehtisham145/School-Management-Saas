# ADR-0018: Remove two-factor authentication; lock out after 15 failed logins

- **Status:** Accepted
- **Date:** 2026-11-11
- **Supersedes:** the TOTP 2FA part of [ADR-0003](0003-auth-sessions-and-rbac.md)

## Context
[ADR-0003](0003-auth-sessions-and-rbac.md) made TOTP two-factor authentication (`django-otp`) mandatory for Super Admins and School Admins. The owner decided not to use it: setting up an authenticator app is a hurdle for school staff, and the product will not offer it.

`django-axes` locked a username + IP pair after 5 failed sign-ins for 1 hour. The owner found that too strict for real users who mistype their password.

## Decision
- Two-factor authentication is removed from the backend and the website:
  - `django-otp` is uninstalled, and the `/api/auth/2fa/...` endpoints are gone.
  - Login and email-code verification sign the user in straight away. Responses no longer carry `requires_2fa` or `requires_2fa_setup`.
  - `HasPolicy` no longer answers `2fa_setup_required`, and `/api/platform/` needs only a signed-in user with `is_platform_admin`.
  - The sign-in page has no 2FA verify, reset or setup steps, and `qrcode.react` is removed.
- The email-code throttle scope is renamed from `twofa` to `email_code`, with the same rate (50/min).
- `AXES_FAILURE_LIMIT` goes from 5 to 15. The cool-off (1 hour) and the lockout key (username + IP) stay the same.

## Consequences
- A stolen password or a stolen mailbox is enough to sign in as any role, including Super Admin, who can create and deactivate schools. This weakens the security posture in [security.md](../security.md) and should be revisited before real school data goes live.
- A password-only Django admin session can now use `/api/platform/`, because the session is no longer checked for a verified device.
- 15 attempts per username + IP gives an attacker three times as many guesses before the lockout. Argon2, the password validators and the `login` throttle (20/min) still apply.
- The `otp_totp_totpdevice` table stays in existing databases. It is unused. A rollback of this release must still find it ([development.md](../development.md#auto-deploy)), so drop it in a later release with a migration.
- Adding 2FA back later would be a new ADR and a new implementation; the session-based auth from ADR-0003 is unchanged and leaves room for it.
