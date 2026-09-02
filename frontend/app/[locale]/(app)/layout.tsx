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
