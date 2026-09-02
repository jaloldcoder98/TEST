"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { DailyNutrition, MealType } from "@/lib/types";

interface FoodLogItemInput {
  name: string;
  estimated_grams: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

interface LogFoodInput {
  meal_type: MealType;
  description?: string;
  items: FoodLogItemInput[];
}

export function useTodayNutrition() {
  return useQuery({ queryKey: ["nutrition", "today"], queryFn: () => api.get<DailyNutrition>("/nutrition/today") });
}

export function useNutritionHistory(from: string, to: string) {
  return useQuery({
    queryKey: ["nutrition", "history", from, to],
    queryFn: () => api.get<DailyNutrition[]>("/nutrition/history", { from, to }),
  });
}

export function useLogFood() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LogFoodInput) => api.post("/nutrition/log", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nutrition"] });
    },
  });
}
