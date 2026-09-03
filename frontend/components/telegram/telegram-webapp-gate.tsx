"use client";

import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FullPageSpinner } from "@/components/ui/spinner";
import { telegramWebAppLogin } from "@/lib/hooks/use-auth";
import { useAuthStore } from "@/lib/stores/auth-store";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        ready: () => void;
        expand: () => void;
        colorScheme?: "light" | "dark";
      };
    };
  }
}

/** Mounted once, above routing (see lib/providers.tsx), so the rest of the app never renders
 * before we've decided whether this page was opened inside Telegram as a Mini App.
 *
 * If it was: silently exchange `Telegram.WebApp.initData` for a session (see
 * app/core/telegram_webapp.py on the backend for how that's verified) before anything else
 * renders — this is what makes "/start -> tap Open App -> straight into the dashboard,
 * already signed in" work, with no login form and no language-picker step. If a session already
 * exists (a returning user reopening the Mini App), this is a no-op past the redirect.
 *
 * If it wasn't (a normal browser tab): `window.Telegram` doesn't exist, so this resolves
 * immediately and the regular site (landing page, manual login, etc.) renders exactly as before —
 * this component changes nothing for the existing web app. */
export function TelegramWebAppGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const locale = (params.locale as string) ?? "uz";
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      const tg = window.Telegram?.WebApp;
      if (!tg || !tg.initData) {
        // Not inside Telegram — nothing to do, render the site as usual.
        if (!cancelled) setReady(true);
        return;
      }

      tg.ready();
      tg.expand();

      if (!useAuthStore.getState().accessToken) {
        try {
          await telegramWebAppLogin(tg.initData);
        } catch {
          // Fall through and render the normal (signed-out) app — the user can still fall back
          // to a manual login/register if, for some reason, Telegram auth didn't work.
        }
      }

      // Send them straight into the dashboard rather than the marketing landing page or a
      // login form they'll never need inside the Mini App.
      const bare = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "");
      const isEntryRoute = bare === "" || bare === "/" || bare === "/login" || bare === "/register";
      if (isEntryRoute && useAuthStore.getState().accessToken) {
        router.replace(`/${locale}/dashboard`);
      }

      if (!cancelled) setReady(true);
    }

    run();
    return () => {
      cancelled = true;
    };
    // Only ever needs to run once, on mount — re-running on every pathname change would fight
    // the very redirect it just performed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) return <FullPageSpinner />;
  return <>{children}</>;
}
