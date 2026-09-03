/* TODO(webapp-first): TZ §11 — locale resolution ignores Telegram. Order should be: the user's saved app language,
 * then Telegram's language_code mapped onto uz/ru/en, then the default. Only the first two
 * are known client-side, so this middleware and the Telegram gate have to agree on who wins.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./i18n";

export default createMiddleware({
  locales,
  defaultLocale,
  localePrefix: "always",
});

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
