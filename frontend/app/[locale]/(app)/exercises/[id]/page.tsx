"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Heart } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { FullPageSpinner } from "@/components/ui/spinner";
import { useExercise, useToggleFavorite } from "@/lib/hooks/use-exercises";
import type { Locale } from "@/i18n";

export default function ExerciseDetailPage() {
  const t = useTranslations("exercises");
  const params = useParams();
  const locale = params.locale as Locale;
  const id = params.id as string;

  const exercise = useExercise(id, locale);
  const toggleFavorite = useToggleFavorite();

  if (exercise.isLoading) return <FullPageSpinner />;
  if (!exercise.data) return null;

  const ex = exercise.data;

  return (
    <div className="space-y-6">
      <Link href={`/${locale}/exercises`} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        {t("backToList")}
      </Link>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="overflow-hidden rounded-2xl border border-border bg-surface-2">
          {/* eslint-disable-next-line @next/next/no-img-element -- external CDN GIF */}
          <img src={ex.gif_url} alt={ex.name} className="h-full w-full object-cover" />
        </div>

        <div className="space-y-5">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-2xl font-bold tracking-tight">{ex.name}</h1>
            <button
              onClick={() => toggleFavorite.mutate({ exerciseId: ex.id, favorited: ex.is_favorited })}
              aria-label={ex.is_favorited ? t("unfavorite") : t("favorite")}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 transition-colors hover:border-primary/40"
            >
              <Heart className={`h-5 w-5 ${ex.is_favorited ? "fill-primary text-primary" : "text-foreground"}`} />
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="primary">{ex.muscle}</Badge>
            <Badge variant="outline">{ex.equipment}</Badge>
            <Badge variant="outline">{ex.body_part}</Badge>
            <Badge variant="outline">{ex.category}</Badge>
          </div>

          {ex.secondary_muscles.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t("secondaryMuscles")}
              </h2>
              <div className="flex flex-wrap gap-2">
                {ex.secondary_muscles.map((m) => (
                  <Badge key={m}>{m}</Badge>
                ))}
              </div>
            </div>
          )}

          {ex.instructions.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t("instructions")}
              </h2>
              <ol className="list-decimal space-y-2 pl-5 text-sm text-foreground/90">
                {ex.instructions.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
