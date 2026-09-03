import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

// The Next.js server proxies /api/v1/* to the backend container over the internal Docker
// network. This is what lets the site work through a single public HTTPS origin (e.g. an ngrok
// tunnel pointed at :3000 for Telegram Mini App testing — see docs/ARCHITECTURE.md §8) without
// also exposing the backend publicly: the browser only ever talks to this one origin, and the
// proxy hop to `backend:8000` happens server-side, inside the Docker network. Overridable via
// BACKEND_INTERNAL_URL for non-Docker native runs (see README's native quickstart).
const BACKEND_INTERNAL_URL = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // Exercise GIFs are served from the source dataset's CDN today (see docs/ARCHITECTURE.md
    // §1.6 on licensing — this stays swappable behind ExerciseMediaProvider on the backend).
    remotePatterns: [{ protocol: "https", hostname: "cdn.jsdelivr.net" }],
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${BACKEND_INTERNAL_URL}/api/v1/:path*` }];
  },
};

export default withNextIntl(nextConfig);
