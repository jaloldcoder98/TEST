/* TODO(webapp-first): TZ §8/§39 — the bottom nav needs safe-area padding utilities (env(safe-area-inset-bottom))
 * so it clears the iOS home indicator inside Telegram. Add them here alongside the existing
 * tokens; the light-theme values themselves live in app/globals.css.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import type { Config } from "tailwindcss";

/**
 * GYM platform design tokens.
 *
 * Direction (spec.md §55): premium modern fitness app, dark-first, in the visual register of
 * Hevy / Strong / Fitbod / Nike Training Club — never a literal copy of any of them. Colors are
 * defined as CSS variables in app/globals.css (HSL triplets) so both the dark theme (default)
 * and a future light theme can swap the same token names.
 */
const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        surface: {
          DEFAULT: "hsl(var(--surface))",
          2: "hsl(var(--surface-2))",
        },
        border: "hsl(var(--border))",
        muted: {
          DEFAULT: "hsl(var(--surface-2))",
          foreground: "hsl(var(--muted-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        success: "hsl(var(--success))",
      },
      borderRadius: {
        lg: "1rem",
        xl: "1.25rem",
        "2xl": "1.75rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -8px hsl(var(--primary) / 0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
