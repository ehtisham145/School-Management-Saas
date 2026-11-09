# ADR-0013: Auto-deploy staging from main

- **Status:** Accepted
- **Date:** 2026-11-07

## Context
Staging ran on a shared Hostinger VPS when this was decided ([ADR-0011](0011-staging-on-hostinger-behind-shared-nginx.md)); it now runs on an OCI VM ([ADR-0015](0015-staging-on-oci-trial-with-caddy.md)) and deploys the same way. Deploying by hand meant logging in as root, pulling, building the images on the server and restarting the stack. Building on the server slows E-Numerak down, and a root login for every release is more access than a deploy needs.

## Decision
- After CI passes on `main`, `.github/workflows/deploy-staging.yml` builds both images, scans them with Trivy and pushes them to GHCR, tagged with the commit SHA.
- It then connects over SSH as a `deploy` user. That key is limited in `authorized_keys` to `command="…/staging/deploy.sh",restrict`, so it can only run the deploy script. The script accepts a full commit SHA and nothing else.
- GHCR access comes from the workflow's own `GITHUB_TOKEN`, sent on stdin. The script logs in through a temporary Docker config that it deletes at exit, so the server never stores a registry credential.
- `staging/deploy.sh` pulls the images, checks out the commit, runs migrations and waits until every service is healthy. If that fails, it puts the previous commit and images back.
- The `staging` GitHub environment holds the SSH key, host and host key, and only `main` can deploy to it. One deploy runs at a time.

## Consequences
- Every merge to `main` reaches staging in a few minutes, and the running version is always a known commit.
- The server no longer builds images, so E-Numerak isn't slowed by releases.
- Rollback restores code and images but not the database. Migrations must stay compatible with the previous release (add first, remove in a later release).
- The `deploy` user is in the `docker` group, which is close to root. The forced command is what limits the CI key, so `deploy.sh` must keep rejecting any input that isn't a commit SHA.
- `deploy.sh` comes from the repo, so anyone who can merge to `main` decides what runs on the server. Branch protection on `main` is part of the server's security.
