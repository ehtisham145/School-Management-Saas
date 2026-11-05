# Dependencies stage: dev packages and the npm cache stay here.
FROM node:24.22.2-trixie-slim AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund


# Build stage: source code stays here.
FROM node:24.22.2-trixie-slim AS build

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

# NEXT_PUBLIC_* values are written into the public JavaScript. Never put a secret in one.
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build \
    && find .next/standalone .next/static -name '*.map' -delete


# Final stage
FROM node:24.22.2-trixie-slim

ARG APP_VERSION=dev
LABEL org.opencontainers.image.source="https://github.com/ehtisham145/School-Management-Saas" \
      org.opencontainers.image.version="$APP_VERSION"

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

# Nothing installs packages at runtime, so the package tools are removed.
# The app user can write only to .next/cache, where optimized images are kept.
RUN rm -rf /usr/local/lib/node_modules /opt/yarn-* \
       /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
       /usr/local/bin/yarn /usr/local/bin/yarnpkg \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home \
       --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && install -d -o 10001 -g 10001 /app/.next/cache

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/en/login').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "server.js"]
