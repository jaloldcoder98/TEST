"use client";

import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FullPageSpinner } from "@/components/ui/spinner";
import { telegramWebAppLogin } from "@/lib/hooks/use-auth";
import { useAuthStore } from "@/lib/stores/auth-store";

/**
 * Mounted above routing (see lib/providers.tsx), so nothing renders before we know whether this
 * page is running inside Telegram.
 *
 * Inside Telegram this is the *only* way a session begins (docs/DECISIONS.md D-10): exchange the
 * `initData` string the client hands us for a session, then go straight to the dashboard. There
 * is no login form to fall back to, because there is no password to type.
 *
 * Session state lives only in memory (D-12), so this runs on every cold open — which is exactly
 * the design: the refresh cookie is an optimisation for warm reloads, and re-authenticating from
 * `initData` is the reliable path that works even where the cookie is blocked (D-15, invariant 16).
 *
 * Outside Telegram, `window.Telegram` does not exist and the app renders the "open in Telegram"
 * page instead (D-21).
 */
export function TelegramWebAppGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const locale = (params.locale as string) ?? "uz";
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;
      if (!tg || !tg.initData) {
        if (!cancelled) setReady(true);
        return;
      }

      tg.ready();
      tg.expand();

      if (!useAuthStore.getState().accessToken) {
        try {
          await telegramWebAppLogin(tg.initData);
        } catch {
          // Render the signed-out app rather than a dead spinner; the API client will retry the
          // same exchange on the next 401 (see recoverSession in lib/api-client.ts).
        }
      }

      const bare = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "");
      if ((bare === "" || bare === "/") && useAuthStore.getState().accessToken) {
        router.replace(`/${locale}/dashboard`);
      }

      if (!cancelled) setReady(true);
    }

    run();
    return () => {
      cancelled = true;
    };
    // Once, on mount: re-running on every pathname change would fight the redirect it just made.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) return <FullPageSpinner />;
  return <>{children}</>;
}
