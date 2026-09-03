"use client";

/* TODO(webapp-first): TZ §13 — the Dashboard is the Mini App's home screen and the spec lists more than this shows:
 * avatar, current weight, protein against target, today's planned workout, weekly workout count,
 * current streak, and the quick-action row (Start Workout / Log Food / Analyze Food / Ask AI /
 * Exercises). Streak and weekly count need backend support in the progress summary.
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Apple, Dumbbell, Plus, Scale } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useTodayNutrition } from "@/lib/hooks/use-nutrition";
import { useProgressSummary } from "@/lib/hooks/use-progress";
import { useWorkouts } from "@/lib/hooks/use-workouts";
import { useAuthStore } from "@/lib/stores/auth-store";
import type { Locale } from "@/i18n";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const params = useParams();
  const locale = params.locale as Locale;
  const user = useAuthStore((s) => s.user);

  const nutrition = useTodayNutrition();
  const workouts = useWorkouts();
  const progress = useProgressSummary();

  const displayName = user?.first_name || user?.username || "";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("greeting", { name: displayName })}</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <div className="mb-3 flex items-center gap-2 text-primary">
            <Apple className="h-5 w-5" />
            <CardTitle className="text-base">{t("todaysNutrition")}</CardTitle>
          </div>
          {nutrition.isLoading ? (
            <Spinner />
          ) : nutrition.data ? (
            <>
              <div className="text-3xl font-extrabold">
                {Math.round(nutrition.data.total_calories)} <span className="text-base font-medium text-muted-foreground">{tc("kcal")}</span>
              </div>
              {nutrition.data.remaining_calories !== null ? (
                <CardDescription>
                  {Math.round(nutrition.data.remaining_calories)} {tc("kcal")} {t("remaining")}
                </CardDescription>
              ) : (
                <CardDescription>{t("noCalorieTarget")}</CardDescription>
              )}
            </>
          ) : null}
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2 text-primary">
            <Dumbbell className="h-5 w-5" />
            <CardTitle className="text-base">{t("recentWorkouts")}</CardTitle>
          </div>
          {workouts.isLoading ? (
            <Spinner />
          ) : workouts.data && workouts.data.length > 0 ? (
            <div className="text-3xl font-extrabold">{workouts.data.length}</div>
          ) : (
            <CardDescription>{t("noWorkouts")}</CardDescription>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2 text-primary">
            <Scale className="h-5 w-5" />
            <CardTitle className="text-base">{t("weightTrend")}</CardTitle>
          </div>
          {progress.isLoading ? (
            <Spinner />
          ) : progress.data && progress.data.weight_trend.length > 0 ? (
            <div className="text-3xl font-extrabold">
              {progress.data.weight_trend[progress.data.weight_trend.length - 1].weight_kg} {tc("kg")}
            </div>
          ) : (
            <CardDescription>{t("noWorkouts")}</CardDescription>
          )}
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("quickLinks")}</h2>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="secondary">
            <Link href={`/${locale}/workouts`}>
              <Plus className="h-4 w-4" />
              {t("createWorkout")}
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/${locale}/nutrition`}>{t("logMeal")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/${locale}/progress`}>{t("logWeight")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/${locale}/exercises`}>{t("browseExercises")}</Link>
          </Button>
        </div>
      </div>

      {workouts.data && workouts.data.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("recentWorkouts")}</h2>
          <div className="space-y-3">
            {workouts.data.slice(0, 5).map((w) => (
              <Link key={w.id} href={`/${locale}/workouts/${w.id}`}>
                <Card className="flex items-center justify-between py-4">
                  <div>
                    <div className="font-semibold">{w.name}</div>
                    <div className="text-sm text-muted-foreground">{w.exercises.length} exercises</div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
