"use client";

import { useRouter, useParams } from "next/navigation";
import { useEffect } from "react";

import { FullPageSpinner } from "@/components/ui/spinner";
import { useAuthStore } from "@/lib/stores/auth-store";

/**
 * Route guard for the app route group.
 *
 * There is no `/login` to send anyone to any more (docs/DECISIONS.md D-10), so an unauthenticated
 * visitor goes to the landing page, which tells them to open the app inside Telegram (D-21).
 *
 * Unlike the previous version this does not wait for storage to hydrate: session state is memory
 * only (D-12), so there is nothing to hydrate. Inside Telegram the gate above has already
 * authenticated by the time this renders; outside it, there was never a session to restore.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();
  const locale = params.locale as string;
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!accessToken) router.replace(`/${locale}`);
  }, [accessToken, router, locale]);

  if (!accessToken) return <FullPageSpinner />;

  return <>{children}</>;
}
