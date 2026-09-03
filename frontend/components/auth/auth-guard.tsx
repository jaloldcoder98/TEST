"use client";

/* TODO(webapp-first): TZ §6/§14 — inside Telegram this guard can dead-end a user: if the stored session is gone it
 * redirects to /login, a page a Mini App user should never see. It should instead re-run the
 * initData exchange, and send users whose onboarding_completed is false to /onboarding.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { useRouter, useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { FullPageSpinner } from "@/components/ui/spinner";
import { useAuthStore } from "@/lib/stores/auth-store";

/** Client-side route guard for the (dashboard) route group — see auth-store.ts for why auth is
 * client-only here rather than SSR/cookie-based. Waits one tick for the zustand persist
 * middleware to hydrate from localStorage before deciding, so a logged-in user never flashes
 * a redirect to /login on a hard refresh. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();
  const locale = params.locale as string;
  const accessToken = useAuthStore((s) => s.accessToken);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated && !accessToken) {
      router.replace(`/${locale}/login`);
    }
  }, [hydrated, accessToken, router, locale]);

  if (!hydrated || !accessToken) return <FullPageSpinner />;

  return <>{children}</>;
}
