import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Bound to Telegram's theme variables so the app matches the client's
        // light/dark theme, with Hevy-ish fallbacks when opened outside Telegram.
        tg: {
          bg: 'var(--tg-theme-bg-color, #0f1115)',
          secondary: 'var(--tg-theme-secondary-bg-color, #171a21)',
          text: 'var(--tg-theme-text-color, #f5f6f8)',
          hint: 'var(--tg-theme-hint-color, #8b93a1)',
          link: 'var(--tg-theme-link-color, #4c8bf5)',
          button: 'var(--tg-theme-button-color, #2f6bff)',
          buttonText: 'var(--tg-theme-button-text-color, #ffffff)',
          destructive: 'var(--tg-theme-destructive-text-color, #ef4444)',
        },
        // Translucent overlays defined in index.css; see the note there for why
        // these are tokens rather than `/opacity` modifiers on tg colors.
        surface: {
          sunken: 'var(--surface-sunken)',
          raised: 'var(--surface-raised)',
          line: 'var(--surface-line)',
          strong: 'var(--surface-strong)',
        },
        accent: {
          DEFAULT: '#2f6bff',
          soft: 'rgba(47, 107, 255, 0.14)',
        },
        success: '#22c55e',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Inter', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      spacing: {
        'safe-b': 'env(safe-area-inset-bottom, 0px)',
      },
    },
  },
  plugins: [],
} satisfies Config;
