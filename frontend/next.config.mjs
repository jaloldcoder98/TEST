import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // Exercise GIFs are served from the source dataset's CDN today (see docs/ARCHITECTURE.md
    // §1.6 on licensing — this stays swappable behind ExerciseMediaProvider on the backend).
    remotePatterns: [{ protocol: "https", hostname: "cdn.jsdelivr.net" }],
  },
};

export default withNextIntl(nextConfig);
