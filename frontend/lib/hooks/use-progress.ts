"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { BodyMeasurement, ProgressSummary } from "@/lib/types";

interface LogWeightInput {
  weight_kg: number;
}

interface LogMeasurementsInput {
  weight_kg?: number;
  body_fat_pct?: number;
  chest_cm?: number;
  waist_cm?: number;
  hips_cm?: number;
  arms_cm?: number;
  thighs_cm?: number;
  notes?: string;
}

export function useProgressSummary() {
  return useQuery({ queryKey: ["progress"], queryFn: () => api.get<ProgressSummary>("/progress") });
}

export function useLogWeight() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LogWeightInput) => api.post<BodyMeasurement>("/progress/weight", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["progress"] }),
  });
}

export function useLogMeasurements() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LogMeasurementsInput) => api.post<BodyMeasurement>("/progress/measurements", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["progress"] }),
  });
}
