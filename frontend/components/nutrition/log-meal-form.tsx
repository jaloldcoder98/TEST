"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useLogFood } from "@/lib/hooks/use-nutrition";
import type { MealType } from "@/lib/types";

interface DraftItem {
  name: string;
  estimated_grams: string;
  calories: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
}

const EMPTY_ITEM: DraftItem = { name: "", estimated_grams: "", calories: "", protein_g: "", carbs_g: "", fat_g: "" };

export function LogMealForm() {
  const t = useTranslations("nutrition");
  const tc = useTranslations("common");
  const logFood = useLogFood();

  const [mealType, setMealType] = useState<MealType>("breakfast");
  const [description, setDescription] = useState("");
  const [items, setItems] = useState<DraftItem[]>([{ ...EMPTY_ITEM }]);

  function updateItem(index: number, field: keyof DraftItem, value: string) {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
  }

  function addItem() {
    setItems((prev) => [...prev, { ...EMPTY_ITEM }]);
  }

  function removeItem(index: number) {
    setItems((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validItems = items.filter((i) => i.name && i.estimated_grams && i.calories);
    if (validItems.length === 0) return;

    await logFood.mutateAsync({
      meal_type: mealType,
      description: description || undefined,
      items: validItems.map((i) => ({
        name: i.name,
        estimated_grams: Number(i.estimated_grams),
        calories: Number(i.calories),
        protein_g: Number(i.protein_g || 0),
        carbs_g: Number(i.carbs_g || 0),
        fat_g: Number(i.fat_g || 0),
      })),
    });

    setMealType("breakfast");
    setDescription("");
    setItems([{ ...EMPTY_ITEM }]);
  }

  return (
    <Card>
      <CardTitle className="mb-4">{t("logMeal")}</CardTitle>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="meal-type">{t("mealType")}</Label>
            <Select id="meal-type" value={mealType} onChange={(e) => setMealType(e.target.value as MealType)}>
              <option value="breakfast">{t("breakfast")}</option>
              <option value="lunch">{t("lunch")}</option>
              <option value="dinner">{t("dinner")}</option>
              <option value="snack">{t("snack")}</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="meal-desc">
              {t("description")} <span className="text-muted-foreground">({tc("optional")})</span>
            </Label>
            <Textarea id="meal-desc" className="min-h-0 h-11 py-2.5" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>

        <div className="space-y-3">
          {items.map((item, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface-2 p-3">
              <div className="mb-2 flex items-center justify-between">
                <Input
                  placeholder={t("itemName")}
                  value={item.name}
                  onChange={(e) => updateItem(i, "name", e.target.value)}
                  className="mr-2 bg-surface"
                />
                {items.length > 1 && (
                  <button type="button" onClick={() => removeItem(i)} className="text-muted-foreground hover:text-destructive">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-5 gap-2">
                {(
                  [
                    ["estimated_grams", t("grams")],
                    ["calories", t("calories")],
                    ["protein_g", t("protein")],
                    ["carbs_g", t("carbs")],
                    ["fat_g", t("fat")],
                  ] as const
                ).map(([field, label]) => (
                  <div key={field}>
                    <label className="mb-1 block text-[11px] text-muted-foreground">{label}</label>
                    <Input
                      type="number"
                      inputMode="decimal"
                      className="h-9 bg-surface px-2 text-sm"
                      value={item[field]}
                      onChange={(e) => updateItem(i, field, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <button type="button" onClick={addItem} className="flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
            <Plus className="h-4 w-4" />
            {t("addItem")}
          </button>
          <Button type="submit" disabled={logFood.isPending}>
            {t("save")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
