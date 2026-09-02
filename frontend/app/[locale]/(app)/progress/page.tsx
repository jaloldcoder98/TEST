"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { FullPageSpinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useLogMeasurements, useLogWeight, useProgressSummary } from "@/lib/hooks/use-progress";

export default function ProgressPage() {
  const t = useTranslations("progress");
  const tc = useTranslations("common");
  const summary = useProgressSummary();
  const logWeight = useLogWeight();
  const logMeasurements = useLogMeasurements();

  const [weight, setWeight] = useState("");
  const [measurements, setMeasurements] = useState({
    body_fat_pct: "",
    chest_cm: "",
    waist_cm: "",
    hips_cm: "",
    arms_cm: "",
    thighs_cm: "",
    notes: "",
  });

  async function handleLogWeight(e: React.FormEvent) {
    e.preventDefault();
    if (!weight) return;
    await logWeight.mutateAsync({ weight_kg: Number(weight) });
    setWeight("");
  }

  async function handleLogMeasurements(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, number | string> = {};
    for (const [key, value] of Object.entries(measurements)) {
      if (value) payload[key] = key === "notes" ? value : Number(value);
    }
    if (Object.keys(payload).length === 0) return;
    await logMeasurements.mutateAsync(payload);
    setMeasurements({ body_fat_pct: "", chest_cm: "", waist_cm: "", hips_cm: "", arms_cm: "", thighs_cm: "", notes: "" });
  }

  const weightData = summary.data?.weight_trend.map((m) => ({ date: m.date.slice(5), weight: m.weight_kg })) ?? [];
  const volumeData =
    summary.data?.volume_trend.map((v) => ({ date: v.date.slice(5), volume: v.total_volume_kg ?? 0 })) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">{t("title")}</h1>

      {summary.isLoading ? (
        <FullPageSpinner />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardTitle className="text-base text-muted-foreground">{t("workoutsCompleted")}</CardTitle>
              <div className="text-3xl font-extrabold">{summary.data?.workout_count ?? 0}</div>
            </Card>
            <Card>
              <CardTitle className="text-base text-muted-foreground">{t("totalVolume")}</CardTitle>
              <div className="text-3xl font-extrabold">
                {summary.data?.total_volume_kg ?? 0} <span className="text-base font-medium text-muted-foreground">{tc("kg")}</span>
              </div>
            </Card>
          </div>

          {weightData.length > 1 && (
            <Card>
              <CardTitle className="mb-4">{t("weightTrend")}</CardTitle>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={weightData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} domain={["auto", "auto"]} />
                    <Tooltip contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                    <Line type="monotone" dataKey="weight" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {volumeData.length > 1 && (
            <Card>
              <CardTitle className="mb-4">{t("volumeTrend")}</CardTitle>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={volumeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <Tooltip contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                    <Line type="monotone" dataKey="volume" stroke="hsl(var(--secondary))" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {weightData.length <= 1 && volumeData.length <= 1 && (
            <p className="text-sm text-muted-foreground">{t("noData")}</p>
          )}
        </>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardTitle className="mb-4">{t("logWeight")}</CardTitle>
          <form onSubmit={handleLogWeight} className="flex items-end gap-3">
            <div className="flex-1">
              <Label htmlFor="weight-kg">{t("weightKg")}</Label>
              <Input id="weight-kg" type="number" inputMode="decimal" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} />
            </div>
            <Button type="submit" disabled={logWeight.isPending}>
              {tc("save")}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle className="mb-4">{t("logMeasurements")}</CardTitle>
          <form onSubmit={handleLogMeasurements} className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ["chest_cm", t("chest")],
                  ["waist_cm", t("waist")],
                  ["hips_cm", t("hips")],
                  ["arms_cm", t("arms")],
                  ["thighs_cm", t("thighs")],
                  ["body_fat_pct", t("bodyFat")],
                ] as const
              ).map(([field, label]) => (
                <div key={field}>
                  <label className="mb-1 block text-[11px] text-muted-foreground">{label}</label>
                  <Input
                    type="number"
                    inputMode="decimal"
                    className="h-9 px-2 text-sm"
                    value={measurements[field]}
                    onChange={(e) => setMeasurements((prev) => ({ ...prev, [field]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
            <Textarea
              placeholder={t("notes")}
              className="min-h-0 h-9 py-2"
              value={measurements.notes}
              onChange={(e) => setMeasurements((prev) => ({ ...prev, notes: e.target.value }))}
            />
            <Button type="submit" className="w-full" disabled={logMeasurements.isPending}>
              {tc("save")}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
