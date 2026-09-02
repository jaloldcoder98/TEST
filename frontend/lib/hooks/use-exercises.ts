"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { ExerciseDetail, LookupItem, PaginatedExercises } from "@/lib/types";

export interface ExerciseFilters {
  muscle?: string;
  equipment?: string;
  bodyPart?: string;
  category?: string;
  q?: string;
  lang?: string;
  page?: number;
}

export function useExercises(filters: ExerciseFilters) {
  return useQuery({
    queryKey: ["exercises", filters],
    queryFn: () =>
      api.get<PaginatedExercises>("/exercises", {
        muscle: filters.muscle,
        equipment: filters.equipment,
        bodyPart: filters.bodyPart,
        category: filters.category,
        q: filters.q,
        lang: filters.lang,
        page: filters.page ?? 1,
      }),
    placeholderData: (prev) => prev,
  });
}

export function useExercise(id: string, lang?: string) {
  return useQuery({
    queryKey: ["exercise", id, lang],
    queryFn: () => api.get<ExerciseDetail>(`/exercises/${id}`, { lang }),
    enabled: !!id,
  });
}

export function useLookups() {
  const muscles = useQuery({ queryKey: ["lookups", "muscles"], queryFn: () => api.get<LookupItem[]>("/exercises/muscles") });
  const equipment = useQuery({
    queryKey: ["lookups", "equipment"],
    queryFn: () => api.get<LookupItem[]>("/exercises/equipment"),
  });
  const bodyParts = useQuery({
    queryKey: ["lookups", "bodyParts"],
    queryFn: () => api.get<LookupItem[]>("/exercises/body-parts"),
  });
  const categories = useQuery({
    queryKey: ["lookups", "categories"],
    queryFn: () => api.get<LookupItem[]>("/exercises/categories"),
  });
  return { muscles, equipment, bodyParts, categories };
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ exerciseId, favorited }: { exerciseId: string; favorited: boolean }) =>
      favorited ? api.delete(`/exercises/${exerciseId}/favorite`) : api.post(`/exercises/${exerciseId}/favorite`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exercises"] });
      queryClient.invalidateQueries({ queryKey: ["exercise"] });
    },
  });
}
