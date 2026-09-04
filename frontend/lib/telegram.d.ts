/** The slice of Telegram's Mini App SDK this app uses.
 *
 * Declared once, globally, because two independent places need it: the gate that authenticates
 * on load, and the API client's silent re-auth path (docs/DECISIONS.md D-15) — which must be
 * able to ask Telegram for fresh `initData` from anywhere a request can 401.
 */
interface TelegramWebApp {
  initData: string;
  ready: () => void;
  expand: () => void;
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
  disableVerticalSwipes?: () => void;
  BackButton?: { show: () => void; hide: () => void; onClick: (cb: () => void) => void };
  HapticFeedback?: { impactOccurred: (style: string) => void; notificationOccurred: (type: string) => void };
}

interface Window {
  Telegram?: { WebApp?: TelegramWebApp };
}
