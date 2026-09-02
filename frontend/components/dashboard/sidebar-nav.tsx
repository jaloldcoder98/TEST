"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Dumbbell,
  LayoutDashboard,
  ListChecks,
  Apple,
  LineChart,
  Bot,
  LogOut,
} from "lucide-react";

import { LanguageSwitcher } from "@/components/landing/language-switcher";
import { useLogout } from "@/lib/hooks/use-auth";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { Locale } from "@/i18n";

const ITEMS = [
  { href: "dashboard", label: "dashboard", icon: LayoutDashboard },
  { href: "exercises", label: "exercises", icon: Dumbbell },
  { href: "workouts", label: "workouts", icon: ListChecks },
  { href: "nutrition", label: "nutrition", icon: Apple },
  { href: "progress", label: "progress", icon: LineChart },
  { href: "ai-coach", label: "aiCoach", icon: Bot },
] as const;

export function SidebarNav({ locale }: { locale: Locale }) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);

  return (
    <div className="flex h-full flex-col gap-6 border-r border-border bg-surface p-5">
      <Link href={`/${locale}/dashboard`} className="flex items-center gap-2 px-2 text-lg font-bold tracking-tight">
        <Dumbbell className="h-6 w-6 text-primary" />
        GYM<span className="text-primary">AI</span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {ITEMS.map(({ href, label, icon: Icon }) => {
          const target = `/${locale}/${href}`;
          const active = pathname === target || pathname.startsWith(`${target}/`);
          return (
            <Link
              key={href}
              href={target}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
              }`}
            >
              <Icon className="h-5 w-5" />
              {t(label)}
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col gap-3 border-t border-border pt-4">
        {user && (
          <div className="px-2 text-sm">
            <div className="font-semibold text-foreground">{user.first_name || user.username}</div>
            <div className="text-xs text-muted-foreground">@{user.username}</div>
          </div>
        )}
        <LanguageSwitcher current={locale} />
        <button
          onClick={logout}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-2 hover:text-destructive"
        >
          <LogOut className="h-5 w-5" />
          {t("logout")}
        </button>
      </div>
    </div>
  );
}
