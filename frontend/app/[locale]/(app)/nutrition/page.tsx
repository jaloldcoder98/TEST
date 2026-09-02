"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { FullPageSpinner } from "@/components/ui/spinner";
import { LogMealForm } from "@/components/nutrition/log-meal-form";
import { useTodayNutrition } from "@/lib/hooks/use-nutrition";

const MEAL_LABEL_KEYS = { breakfast: "breakfast", lunch: "lunch", dinner: "dinner", snack: "snack" } as const;

export default function NutritionPage() {
  const t = useTranslations("nutrition");
  const tc = useTranslations("common");
  const nutrition = useTodayNutrition();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>

      {nutrition.isLoading ? (
        <FullPageSpinner />
      ) : (
        nutrition.data && (
          <Card>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <CardTitle className="text-base text-muted-foreground">{t("totalToday")}</CardTitle>
                <div className="text-3xl font-extrabold">
                  {Math.round(nutrition.data.total_calories)} <span className="text-base font-medium text-muted-foreground">{tc("kcal")}</span>
                </div>
              </div>
              {nutrition.data.calorie_target !== null ? (
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">{t("target")}</div>
                  <div className="text-lg font-semibold">
                    {nutrition.data.calorie_target} {tc("kcal")}
                  </div>
                  <div className="text-sm text-primary">
                    {Math.round(nutrition.data.remaining_calories ?? 0)} {tc("kcal")} {t("remaining")}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noTarget")}</p>
              )}
            </div>
            <div className="mt-4 flex gap-4 text-sm">
              <span>
                {t("protein")}: <strong>{Math.round(nutrition.data.protein_g)}{tc("g")}</strong>
              </span>
              <span>
                {t("carbs")}: <strong>{Math.round(nutrition.data.carbs_g)}{tc("g")}</strong>
              </span>
              <span>
                {t("fat")}: <strong>{Math.round(nutrition.data.fat_g)}{tc("g")}</strong>
              </span>
            </div>
          </Card>
        )
      )}

      <LogMealForm />

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("today")}</h2>
        {nutrition.data && nutrition.data.logs.length > 0 ? (
          <div className="space-y-3">
            {nutrition.data.logs.map((log) => (
              <Card key={log.id}>
                <div className="mb-2 flex items-center justify-between">
                  <Badge variant="primary">{t(MEAL_LABEL_KEYS[log.meal_type])}</Badge>
                  <span className="font-semibold">
                    {Math.round(log.total_calories)} {tc("kcal")}
                  </span>
                </div>
                {log.description && <p className="mb-2 text-sm text-muted-foreground">{log.description}</p>}
                <ul className="space-y-1 text-sm text-foreground/90">
                  {log.items.map((item) => (
                    <li key={item.id} className="flex justify-between">
                      <span>
                        {item.name} ({item.estimated_grams}{tc("g")})
                      </span>
                      <span className="text-muted-foreground">
                        {Math.round(item.calories)} {tc("kcal")}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("noLogsToday")}</p>
        )}
      </div>
    </div>
  );
}
