/* TODO(webapp-first): TZ §10 — <html className="dark"> hardcodes the theme. The Mini App has to follow Telegram:
 * read colorScheme/themeParams and map --tg-theme-* onto our own tokens, while still working
 * standalone in a browser (see lib/telegram/theme.ts in the plan).
 *
 * TZ §40 — PWA metadata is missing entirely: manifest link, themeColor, and a viewport with
 * viewport-fit=cover (needed before the bottom nav's safe-area insets do anything).
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import Script from "next/script";

import { locales } from "@/i18n";
import { Providers } from "@/lib/providers";
import "../globals.css";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export const metadata: Metadata = {
  title: "GYM AI — Personal Fitness Coach",
  description:
    "1,300+ exercises, AI workout coaching, food calorie analysis, and progress tracking — on the web and on Telegram.",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} className="dark">
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        {/* Harmless outside Telegram — window.Telegram just never gets set, and
            components/telegram/telegram-webapp-gate.tsx treats that as "not a Mini App" and
            renders the normal site. beforeInteractive so it's present before that gate's effect
            runs. */}
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <NextIntlClientProvider messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
