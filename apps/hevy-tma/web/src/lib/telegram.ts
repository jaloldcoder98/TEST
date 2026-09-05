import WebApp from '@twa-dev/sdk';

/**
 * Thin wrapper around @twa-dev/sdk so the rest of the app never has to guard
 * against running outside Telegram (a plain browser tab during development).
 */

declare global {
  interface Window {
    Telegram?: { WebApp?: { initData?: string } };
  }
}

/** True when the page was actually opened inside a Telegram client. */
export const isTelegramClient = (): boolean =>
  typeof window !== 'undefined' && Boolean(window.Telegram?.WebApp?.initData);

/** Raw signed payload the backend verifies. Empty string outside Telegram. */
export const getInitData = (): string => {
  try {
    return WebApp.initData ?? '';
  } catch {
    return '';
  }
};

/** Prepare the viewport: expand, disable pull-to-close, apply the theme. */
export function initTelegram(): void {
  try {
    WebApp.ready();
    WebApp.expand();
    WebApp.disableVerticalSwipes?.();
    WebApp.setHeaderColor?.('secondary_bg_color');
    // Drives the light/dark surface tokens in index.css.
    document.documentElement.dataset.theme = WebApp.colorScheme ?? 'dark';
  } catch {
    // Not inside Telegram — the app still works, just without the chrome.
  }
}

type ImpactStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';

export const haptic = {
  impact(style: ImpactStyle = 'light'): void {
    try {
      WebApp.HapticFeedback.impactOccurred(style);
    } catch {
      /* no-op outside Telegram */
    }
  },
  success(): void {
    try {
      WebApp.HapticFeedback.notificationOccurred('success');
    } catch {
      /* no-op */
    }
  },
  warning(): void {
    try {
      WebApp.HapticFeedback.notificationOccurred('warning');
    } catch {
      /* no-op */
    }
  },
  selection(): void {
    try {
      WebApp.HapticFeedback.selectionChanged();
    } catch {
      /* no-op */
    }
  },
};

/**
 * Drive Telegram's native main button. Returns a cleanup function, so a
 * component can own the button for as long as it is mounted.
 */
export function setMainButton(options: {
  text: string;
  onClick: () => void;
  visible?: boolean;
  progress?: boolean;
  enabled?: boolean;
}): () => void {
  const { text, onClick, visible = true, progress = false, enabled = true } = options;

  try {
    const button = WebApp.MainButton;
    button.setText(text);
    button.offClick(onClick);
    button.onClick(onClick);

    if (enabled) button.enable();
    else button.disable();

    if (progress) button.showProgress(false);
    else button.hideProgress();

    if (visible) button.show();
    else button.hide();

    return () => {
      try {
        button.offClick(onClick);
        button.hide();
      } catch {
        /* no-op */
      }
    };
  } catch {
    return () => undefined;
  }
}

/** Telegram's native confirm dialog, with a browser fallback. */
export function confirmDialog(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      WebApp.showConfirm(message, (confirmed) => resolve(confirmed));
    } catch {
      resolve(window.confirm(message));
    }
  });
}

export function closeApp(): void {
  try {
    WebApp.close();
  } catch {
    /* no-op */
  }
}
