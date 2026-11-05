# ADR-0012: WhiteNoise for Django static files

- **Status:** Accepted
- **Date:** 2026-11-05

## Context
The Django admin needs its CSS and JavaScript in production, where Django doesn't serve static files. On staging, nginx belongs to another project ([ADR-0011](0011-staging-on-hostinger-behind-shared-nginx.md)), so giving it a volume of our files would tie the two projects together. Production will use Caddy, so an nginx-only answer wouldn't carry over.

## Decision
Use WhiteNoise in production settings only. The files are collected into the backend image at build time and served by the backend, with hashed names and compressed copies. The proxy forwards `/static/` to the backend.

## Consequences
- Static files ship with the image, so they always match the code, and the same setup works behind nginx and Caddy.
- The backend handles these requests. That's fine for now, because only the admin uses these files; the public site's assets come from Next.js.
- `collectstatic` fails the image build if a stylesheet points to a missing file.
