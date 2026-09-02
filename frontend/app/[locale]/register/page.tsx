"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { useRegister } from "@/lib/hooks/use-auth";
import type { Locale } from "@/i18n";

export default function RegisterPage() {
  const t = useTranslations("auth");
  const tc = useTranslations("common");
  const params = useParams();
  const locale = params.locale as Locale;
  const router = useRouter();
  const register = useRegister();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await register.mutateAsync({
        username,
        password,
        email: email || undefined,
        first_name: firstName || undefined,
        language: locale,
      });
      router.push(`/${locale}/dashboard`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "USERNAME_TAKEN") {
        setError(t("usernameTaken"));
      } else if (err instanceof ApiError && err.code === "EMAIL_TAKEN") {
        setError(t("emailTaken"));
      } else {
        setError(t("genericError"));
      }
    }
  }

  return (
    <AuthShell title={t("registerTitle")} subtitle={t("registerSubtitle")} locale={locale}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <Label htmlFor="username">{t("username")}</Label>
          <Input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            autoComplete="username"
          />
        </div>
        <div>
          <Label htmlFor="firstName">
            {t("firstName")} <span className="text-muted-foreground">({tc("optional")})</span>
          </Label>
          <Input id="firstName" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="email">
            {t("email")} <span className="text-muted-foreground">({tc("optional")})</span>
          </Label>
          <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        </div>
        <div>
          <Label htmlFor="password">{t("password")}</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" size="lg" disabled={register.isPending}>
          {t("submitRegister")}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("haveAccount")}{" "}
        <Link href={`/${locale}/login`} className="font-medium text-primary hover:underline">
          {t("loginLink")}
        </Link>
      </p>
    </AuthShell>
  );
}
