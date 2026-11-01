import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Dev-only: proxies /api/* to the Django backend so the browser sees the
// frontend and API as the same origin (matches production, where Caddy
// routes /api directly to Django and this rewrite never runs).
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Belt-and-braces: don't let Next normalize trailing slashes on its own
  // routes out from under the /api/* rewrite below.
  skipTrailingSlashRedirect: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      {
        // `:path*` captures segments only, never a trailing slash — so the
        // destination needs one appended explicitly, or Django's
        // APPEND_SLASH 500s on POST (every endpoint here ends in `/`).
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*/`,
      },
    ];
  },
};

const withNextIntl = createNextIntlPlugin();
export default withNextIntl(nextConfig);
