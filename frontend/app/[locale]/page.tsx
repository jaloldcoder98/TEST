import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import {
  Dumbbell,
  Bot,
  ClipboardList,
  Apple,
  LineChart,
  Send,
  ArrowRight,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardDescription } from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/landing/language-switcher";
import type { Locale } from "@/i18n";

const FEATURE_ICONS = [Dumbbell, Bot, ClipboardList, Apple, LineChart, Send] as const;
const FEATURE_KEYS = [
  "exercises",
  "ai",
  "tracking",
  "nutrition",
  "progress",
  "telegram",
] as const;

export default async function LandingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = (await params) as { locale: Locale };
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "landing" });
  const nav = await getTranslations({ locale, namespace: "nav" });

  return (
    <div className="relative overflow-hidden">
      {/* Ambient glow — sets the "premium fitness" tone without a hero photo. */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[-10rem] h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]"
      />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <Dumbbell className="h-6 w-6 text-primary" />
          GYM<span className="text-primary">AI</span>
        </div>
        <nav className="hidden items-center gap-8 text-sm font-medium text-muted-foreground md:flex">
          <Link href={`/${locale}/exercises`} className="hover:text-foreground">
            {nav("exercises")}
          </Link>
          <Link href={`/${locale}/workouts`} className="hover:text-foreground">
            {nav("workouts")}
          </Link>
          <Link href={`/${locale}/nutrition`} className="hover:text-foreground">
            {nav("nutrition")}
          </Link>
          <Link href={`/${locale}/ai-coach`} className="hover:text-foreground">
            {nav("aiCoach")}
          </Link>
        </nav>
        <div className="flex items-center gap-3">
          <LanguageSwitcher current={locale} />
          <Button asChild size="sm" variant="secondary" className="hidden sm:inline-flex">
            <Link href={`/${locale}/login`}>{nav("login")}</Link>
          </Button>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-6">
        <section className="flex flex-col items-center py-20 text-center sm:py-28">
          <span className="mb-6 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-primary">
            {t("heroBadge")}
          </span>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-6xl">
            {t("heroTitle")}
          </h1>
          <p className="mt-6 max-w-xl text-balance text-lg text-muted-foreground">
            {t("heroLead")}
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href={`/${locale}/register`}>
                {t("cta1")}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link href={`/${locale}/ai-coach`}>{t("cta2")}</Link>
            </Button>
          </div>

          <div className="mt-16 grid w-full max-w-2xl grid-cols-3 gap-4 border-t border-border pt-10">
            {[
              ["1300+", "exercises"],
              ["19", "muscles"],
              ["3", "languages"],
            ].map(([value, label]) => (
              <div key={label}>
                <div className="text-3xl font-extrabold text-primary">{value}</div>
                <div className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                  {label}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 pb-28 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURE_KEYS.map((key, i) => {
            const Icon = FEATURE_ICONS[i];
            return (
              <Card key={key}>
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <CardTitle>{t(`sections.${key}Title`)}</CardTitle>
                <CardDescription>{t(`sections.${key}Body`)}</CardDescription>
              </Card>
            );
          })}
        </section>
      </main>
    </div>
  );
}
