"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Calendar, Dumbbell } from "lucide-react";

import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { FullPageSpinner } from "@/components/ui/spinner";
import { CreateWorkoutDialog } from "@/components/workouts/create-workout-dialog";
import { useWorkouts } from "@/lib/hooks/use-workouts";
import type { Locale } from "@/i18n";

export default function WorkoutsPage() {
  const t = useTranslations("workouts");
  const params = useParams();
  const locale = params.locale as Locale;
  const workouts = useWorkouts();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>
        <CreateWorkoutDialog />
      </div>

      {workouts.isLoading ? (
        <FullPageSpinner />
      ) : workouts.data && workouts.data.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workouts.data.map((w) => (
            <Link key={w.id} href={`/${locale}/workouts/${w.id}`}>
              <Card className="h-full">
                <CardTitle>{w.name}</CardTitle>
                {w.description && <CardDescription>{w.description}</CardDescription>}
                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Dumbbell className="h-3.5 w-3.5" />
                    {t("exercisesCount", { count: w.exercises.length })}
                  </span>
                  {w.day && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {w.day}
                    </span>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      )}
    </div>
  );
}
