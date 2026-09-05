export type SetType = 'WARMUP' | 'NORMAL' | 'DROP' | 'FAILURE';
export type WorkoutStatus = 'IN_PROGRESS' | 'COMPLETED' | 'DISCARDED';
export type ExerciseKind =
  | 'WEIGHT_REPS'
  | 'BODYWEIGHT_REPS'
  | 'WEIGHTED_BODYWEIGHT'
  | 'DURATION'
  | 'DISTANCE_DURATION';

export type MuscleGroup =
  | 'CHEST' | 'BACK' | 'SHOULDERS' | 'BICEPS' | 'TRICEPS' | 'FOREARMS' | 'ABS'
  | 'QUADS' | 'HAMSTRINGS' | 'GLUTES' | 'CALVES' | 'ABDUCTORS' | 'ADDUCTORS'
  | 'TRAPS' | 'NECK' | 'CARDIO' | 'FULL_BODY' | 'OTHER';

export type PersonalRecordType =
  | 'MAX_WEIGHT'
  | 'MAX_REPS'
  | 'BEST_SET_VOLUME'
  | 'ESTIMATED_1RM';

export interface Exercise {
  id: string;
  slug: string;
  name: string;
  muscleGroup: MuscleGroup;
  secondaryMuscles?: MuscleGroup[];
  equipment: string;
  kind: ExerciseKind;
  thumbUrl: string | null;
  imageUrl?: string | null;
  isCustom?: boolean;
}

/** A set as it lives in the client while the workout is being logged. */
export interface DraftSet {
  /** Client-side id; the server assigns the real one on save. */
  localId: string;
  setType: SetType;
  weightKg: number | null;
  reps: number | null;
  rpe: number | null;
  isCompleted: boolean;
  completedAt: string | null;
  /** Values from the same set index last time, shown as placeholder. */
  previous?: { weightKg: number | null; reps: number | null } | null;
}

export interface DraftExercise {
  localId: string;
  exercise: Exercise;
  notes: string | null;
  restSeconds: number | null;
  sets: DraftSet[];
}

export interface CurrentUser {
  id: string;
  telegramId: string;
  username: string | null;
  firstName: string | null;
  lastName: string | null;
  photoUrl: string | null;
  languageCode: string | null;
  unit: 'KG' | 'LB';
  defaultRestSeconds: number;
}

export interface PersonalRecordHit {
  exerciseId: string;
  exerciseName: string;
  type: PersonalRecordType;
  value: number;
  previousValue: number | null;
}

export interface StatsSummary {
  totals: {
    workouts: number;
    volumeKg: number;
    sets: number;
    reps: number;
    durationSec: number;
    personalRecords: number;
  };
  weeklyVolume: { weekStart: string; volumeKg: number; workouts: number }[];
}

export interface PersonalRecordItem {
  id: string;
  type: PersonalRecordType;
  value: number;
  weightKg: number | null;
  reps: number | null;
  achievedAt: string;
  exercise: { id: string; name: string; muscleGroup: MuscleGroup; thumbUrl: string | null };
}

export interface WorkoutSummary {
  id: string;
  title: string;
  status: WorkoutStatus;
  startedAt: string;
  durationSec: number | null;
  totalVolumeKg: number;
  totalSets: number;
  totalReps: number;
  exercises: {
    id: string;
    exercise: Pick<Exercise, 'id' | 'name' | 'muscleGroup' | 'thumbUrl'>;
    sets: { id: string; setNumber: number; setType: SetType; weightKg: number | null; reps: number | null }[];
  }[];
}
