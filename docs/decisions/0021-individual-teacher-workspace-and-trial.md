# ADR-0021: Individual teachers get a private workspace and a 7-day trial

- **Status:** Accepted
- **Date:** 2026-11-18

## Context
The client wants a teacher to sign up alone, without a school, and try the product free for 7 days. Everything in the system belongs to a school: tenancy, memberships, permissions and subscriptions.

## Decision
- An individual teacher gets a private workspace: a `School` row with `kind = individual`, and one `TEACHER` membership. Tenant isolation, selectors and cross-tenant tests work the same as for a real school. Workspaces are left out of the Super Admin's school lists, counts and usage.
- The trial is a normal active `Subscription` on the Teacher plan with `is_trial = true`, price 0 and an end date 7 days after sign-up. The nightly expiry job ends it like any other subscription.
- Sign-up has two steps. The teacher sends their details and receives a 6-digit code by email. They send the details again with the code, and only then are the account, workspace and trial created in one transaction.
- `TeacherSignupCode` holds only the email and the hashed code. The password is never stored before the email is proven, so nobody can plant a password on a sign-up that someone else finishes.
- The request answers the same whether or not the email is registered. A registered email receives a reminder to sign in, so the form can't be used to find accounts.
- The teacher's username is their lowercase email, and login accepts it in any letter case.
- Accepting the privacy policy is required, and the time is kept in the audit log entry for the trial.

## Consequences
- One email gets one trial, because an email can belong to only one account.
- Access is not blocked yet when a trial ends. Read-only mode, plan limits, reminder emails and data deletion are still to be built.
- There is no payment yet. A paid plan is activated by the Super Admin, who must expire the trial first.
- Real teachers must not sign up until production runs in Saudi Arabia. Staging is outside the Kingdom and holds test data only.
- The privacy policy is still a draft, and Terms of Service don't exist yet. Both are needed before public launch.
