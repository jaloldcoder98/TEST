import { getInitData } from './telegram';
import type {
  CurrentUser,
  Exercise,
  PersonalRecordHit,
  PersonalRecordItem,
  StatsSummary,
  WorkoutSummary,
} from '../types';

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:4000/api';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string; details?: unknown };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      // Every request carries the signed payload; the server re-verifies it.
      'X-Telegram-Init-Data': getInitData(),
      ...init.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const body = payload as ErrorBody;
    throw new ApiError(
      response.status,
      body.error?.code ?? 'UNKNOWN',
      body.error?.message ?? `Request failed with ${response.status}`,
      body.error?.details,
    );
  }

  return payload as T;
}

/** Shape POSTed to `POST /api/workouts`. */
export interface CreateWorkoutPayload {
  title: string;
  notes?: string | null;
  status: 'COMPLETED' | 'DISCARDED';
  startedAt: string;
  finishedAt: string;
  durationSec: number;
  exercises: {
    exerciseId: string;
    notes?: string | null;
    restSeconds?: number | null;
    sets: {
      setType: string;
      weightKg: number | null;
      reps: number | null;
      rpe: number | null;
      isCompleted: boolean;
      completedAt: string | null;
    }[];
  }[];
}

export const api = {
  me: () => request<{ user: CurrentUser }>('/me'),

  listExercises: (params: { q?: string; muscleGroup?: string; limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.muscleGroup) search.set('muscleGroup', params.muscleGroup);
    if (params.limit) search.set('limit', String(params.limit));
    const query = search.toString();
    return request<{ items: Exercise[]; nextCursor: string | null }>(
      `/exercises${query ? `?${query}` : ''}`,
    );
  },

  muscleGroups: () =>
    request<{ items: { muscleGroup: string; count: number }[] }>('/exercises/muscle-groups'),

  createWorkout: (payload: CreateWorkoutPayload) =>
    request<{ workout: WorkoutSummary; personalRecords: PersonalRecordHit[] }>('/workouts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listWorkouts: (limit = 20) =>
    request<{ items: WorkoutSummary[]; nextCursor: string | null }>(`/workouts?limit=${limit}`),

  statsSummary: () => request<StatsSummary>('/stats/summary'),

  personalRecords: () => request<{ items: PersonalRecordItem[] }>('/stats/personal-records'),
};
