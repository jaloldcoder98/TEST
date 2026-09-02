"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { Workout, WorkoutSession } from "@/lib/types";

interface WorkoutExerciseInput {
  exercise_id: string;
  order: number;
  notes?: string;
}

interface CreateWorkoutInput {
  name: string;
  description?: string;
  day?: string;
  exercises: WorkoutExerciseInput[];
}

interface LogSetInput {
  workout_exercise_id: string;
  set_number: number;
  reps?: number;
  weight_kg?: number;
  completed: boolean;
}

export function useWorkouts() {
  return useQuery({ queryKey: ["workouts"], queryFn: () => api.get<Workout[]>("/workouts") });
}

export function useWorkout(id: string) {
  return useQuery({
    queryKey: ["workout", id],
    queryFn: () => api.get<Workout>(`/workouts/${id}`),
    enabled: !!id,
  });
}

export function useCreateWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateWorkoutInput) => api.post<Workout>("/workouts", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workouts"] }),
  });
}

export function useDeleteWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/workouts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workouts"] }),
  });
}

export function useStartWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (workoutId: string) => api.post<WorkoutSession>(`/workouts/${workoutId}/start`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workouts"] }),
  });
}

// There is no GET /workout-sessions/{id} on the backend (docs/API.md) — a session is only
// reachable via the response of start/log-set/finish, so the session-tracking page keeps it as
// local component state seeded from useStartWorkout's result rather than through react-query.
export function useLogSet(sessionId: string) {
  return useMutation({
    mutationFn: (input: LogSetInput) => api.post(`/workout-sessions/${sessionId}/sets`, input),
  });
}

export function useFinishSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.post<WorkoutSession>(`/workout-sessions/${sessionId}/finish`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workouts"] });
      queryClient.invalidateQueries({ queryKey: ["progress"] });
    },
  });
}
