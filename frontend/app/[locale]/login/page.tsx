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
import { useLogin } from "@/lib/hooks/use-auth";

export default function LoginPage() {
  const t = useTranslations("auth");
  const params = useParams();
  const locale = params.locale as string;
  const router = useRouter();
  const login = useLogin();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ username, password });
      router.push(`/${locale}/dashboard`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "UNAUTHORIZED") {
        setError(t("invalidCredentials"));
      } else {
        setError(t("genericError"));
      }
    }
  }

  return (
    <AuthShell title={t("loginTitle")} subtitle={t("loginSubtitle")} locale={locale}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <Label htmlFor="username">{t("username")}</Label>
          <Input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
        </div>
        <div>
          <Label htmlFor="password">{t("password")}</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" size="lg" disabled={login.isPending}>
          {t("submitLogin")}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("noAccount")}{" "}
        <Link href={`/${locale}/register`} className="font-medium text-primary hover:underline">
          {t("registerLink")}
        </Link>
      </p>
    </AuthShell>
  );
}
