"use client";

/* TODO(webapp-first): TZ §31 — the card below loads ex.gif_url, i.e. the full animated GIF, for every exercise in
 * the list. ExerciseSummary already carries image_url (the CDN thumbnail, imported by
 * backend/scripts/import_exercises.py); use it here and keep the GIF for the detail page.
 * Across 1,323 exercises this is the single biggest startup-cost win available (audit §4.5).
 * See docs/WEBAPP_FIRST_AUDIT.md for the full plan.
 */

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Heart, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { FullPageSpinner } from "@/components/ui/spinner";
import { useExercises, useLookups, useToggleFavorite } from "@/lib/hooks/use-exercises";
import type { Locale } from "@/i18n";

export default function ExercisesPage() {
  const t = useTranslations("exercises");
  const tc = useTranslations("common");
  const params = useParams();
  const locale = params.locale as Locale;

  const [search, setSearch] = useState("");
  const [muscle, setMuscle] = useState("");
  const [equipment, setEquipment] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);

  const { muscles, equipment: equipmentList, bodyParts, categories } = useLookups();
  const exercises = useExercises({
    q: search || undefined,
    muscle: muscle || undefined,
    equipment: equipment || undefined,
    bodyPart: bodyPart || undefined,
    category: category || undefined,
    lang: locale,
    page,
  });
  const toggleFavorite = useToggleFavorite();

  function resetPage<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setPage(1);
    };
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>

      <div className="space-y-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => resetPage(setSearch)(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="pl-11"
          />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Select value={muscle} onChange={(e) => resetPage(setMuscle)(e.target.value)}>
            <option value="">{`${t("muscle")}: ${tc("all")}`}</option>
            {muscles.data?.map((m) => (
              <option key={m.slug} value={m.slug}>
                {m.slug} ({m.count})
              </option>
            ))}
          </Select>
          <Select value={equipment} onChange={(e) => resetPage(setEquipment)(e.target.value)}>
            <option value="">{`${t("equipment")}: ${tc("all")}`}</option>
            {equipmentList.data?.map((m) => (
              <option key={m.slug} value={m.slug}>
                {m.slug} ({m.count})
              </option>
            ))}
          </Select>
          <Select value={bodyPart} onChange={(e) => resetPage(setBodyPart)(e.target.value)}>
            <option value="">{`${t("bodyPart")}: ${tc("all")}`}</option>
            {bodyParts.data?.map((m) => (
              <option key={m.slug} value={m.slug}>
                {m.slug} ({m.count})
              </option>
            ))}
          </Select>
          <Select value={category} onChange={(e) => resetPage(setCategory)(e.target.value)}>
            <option value="">{`${t("category")}: ${tc("all")}`}</option>
            {categories.data?.map((m) => (
              <option key={m.slug} value={m.slug}>
                {m.slug} ({m.count})
              </option>
            ))}
          </Select>
        </div>
      </div>

      {exercises.isLoading ? (
        <FullPageSpinner />
      ) : exercises.data && exercises.data.items.length > 0 ? (
        <>
          <p className="text-sm text-muted-foreground">{t("resultsCount", { count: exercises.data.total })}</p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {exercises.data.items.map((ex) => (
              <div key={ex.id} className="group relative overflow-hidden rounded-2xl border border-border bg-surface transition-colors hover:border-primary/40">
                <Link href={`/${locale}/exercises/${ex.id}`}>
                  <div className="aspect-square w-full bg-surface-2">
                    {/* eslint-disable-next-line @next/next/no-img-element -- external CDN GIFs, not optimizable by next/image without a remote-pattern allowlist per source */}
                    <img src={ex.gif_url} alt={ex.name} className="h-full w-full object-cover" loading="lazy" />
                  </div>
                  <div className="p-3">
                    <div className="truncate text-sm font-semibold">{ex.name}</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Badge variant="outline">{ex.muscle}</Badge>
                    </div>
                  </div>
                </Link>
                <button
                  onClick={() => toggleFavorite.mutate({ exerciseId: ex.id, favorited: ex.is_favorited })}
                  aria-label={ex.is_favorited ? t("unfavorite") : t("favorite")}
                  className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-background/70 backdrop-blur transition-colors hover:bg-background"
                >
                  <Heart className={`h-4 w-4 ${ex.is_favorited ? "fill-primary text-primary" : "text-foreground"}`} />
                </button>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t("previous")}
            </Button>
            <span className="text-sm text-muted-foreground">{t("page", { page, totalPages: exercises.data.total_pages })}</span>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= exercises.data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("next")}
            </Button>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">{t("noResults")}</p>
      )}
    </div>
  );
}
