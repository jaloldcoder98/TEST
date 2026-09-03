/* TODO(webapp-first): TZ §8/§39 — this layout is desktop-only: grid-cols-[16rem_1fr] renders a 16rem sidebar on a
 * phone, which is the primary target (Telegram mobile). Needs to invert: mobile-first content
 * column with a fixed bottom nav (Home / Workout / Exercises / Nutrition / Profile) plus the
 * AI floating action button, and the sidebar only from lg: upward.
 * New: components/nav/bottom-nav.tsx and components/ai/ai-fab.tsx. Remember the bottom safe-area
 * inset so the nav clears the iOS home indicator inside Telegram.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { AuthGuard } from "@/components/auth/auth-guard";
import { SidebarNav } from "@/components/dashboard/sidebar-nav";
import type { Locale } from "@/i18n";

export default async function AppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = (await params) as { locale: Locale };

  return (
    <AuthGuard>
      <div className="grid min-h-screen grid-cols-[16rem_1fr]">
        <aside className="sticky top-0 h-screen">
          <SidebarNav locale={locale} />
        </aside>
        <main className="min-w-0 px-8 py-8">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}
