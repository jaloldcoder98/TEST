// Mirrors backend/app/schemas/*.py and backend/app/models/enums.py exactly — keep these two in
// sync by hand (no shared codegen yet; a Phase 9+ improvement would be an OpenAPI-generated
// client instead).

export type Language = "uz" | "ru" | "en";
export type Gender = "male" | "female";
export type Goal =
  | "lose_weight"
  | "maintain_weight"
  | "gain_muscle"
  | "gain_weight"
  | "improve_fitness"
  | "strength";
export type ExperienceLevel = "beginner" | "intermediate" | "advanced";
export type ActivityLevel =
  | "sedentary"
  | "lightly_active"
  | "moderately_active"
  | "very_active"
  | "extra_active";
export type SessionStatus = "in_progress" | "paused" | "completed" | "cancelled";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack";

export interface UserProfile {
  date_of_birth: string | null;
  gender: Gender | null;
  height_cm: number | null;
  weight_kg: number | null;
  goal: Goal | null;
  experience_level: ExperienceLevel | null;
  activity_level: ActivityLevel | null;
  daily_calorie_target: number | null;
  protein_target_g: number | null;
  carbs_target_g: number | null;
  fat_target_g: number | null;
}

export interface User {
  id: string;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  language: Language;
  profile: UserProfile | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LookupItem {
  slug: string;
  count: number;
}

export interface ExerciseSummary {
  id: string;
  slug: string;
  name: string;
  muscle: string;
  body_part: string;
  equipment: string;
  category: string;
  gif_url: string;
  image_url: string | null;
  is_favorited: boolean;
}

export interface ExerciseDetail extends ExerciseSummary {
  secondary_muscles: string[];
  instructions: string[];
  source: string;
  source_url: string | null;
  is_machine_translated: boolean;
}

export interface PaginatedExercises {
  items: ExerciseSummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface WorkoutExercise {
  id: string;
  exercise_id: string;
  order: number;
  notes: string | null;
}

export interface Workout {
  id: string;
  name: string;
  description: string | null;
  day: string | null;
  duration_minutes: number | null;
  exercises: WorkoutExercise[];
}

export interface WorkoutSet {
  id: string;
  workout_exercise_id: string;
  set_number: number;
  reps: number | null;
  weight_kg: number | null;
  duration_seconds: number | null;
  rest_seconds: number | null;
  completed: boolean;
  notes: string | null;
}

export interface WorkoutSession {
  id: string;
  workout_id: string;
  status: SessionStatus;
  started_at: string;
  finished_at: string | null;
  total_volume_kg: number | null;
  total_sets: number | null;
  total_reps: number | null;
  estimated_calories: number | null;
  sets: WorkoutSet[];
}

export interface FoodLogItem {
  id: string;
  name: string;
  estimated_grams: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  confidence: number | null;
}

export interface FoodLog {
  id: string;
  date: string;
  meal_type: MealType;
  description: string | null;
  image_url: string | null;
  total_calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  ai_confidence: number | null;
  items: FoodLogItem[];
}

export interface DailyNutrition {
  date: string;
  total_calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  calorie_target: number | null;
  remaining_calories: number | null;
  logs: FoodLog[];
}

export interface BodyMeasurement {
  id: string;
  date: string;
  weight_kg: number | null;
  body_fat_pct: number | null;
  chest_cm: number | null;
  waist_cm: number | null;
  hips_cm: number | null;
  arms_cm: number | null;
  thighs_cm: number | null;
  notes: string | null;
}

export interface WorkoutVolumePoint {
  date: string;
  total_volume_kg: number | null;
  estimated_calories: number | null;
}

export interface ProgressSummary {
  weight_trend: BodyMeasurement[];
  workout_count: number;
  total_volume_kg: number;
  volume_trend: WorkoutVolumePoint[];
}

export interface ApiErrorBody {
  success: false;
  error: { code: string; message: string };
}

export interface ChatResponse {
  conversation_id: string;
  context_type: string;
  message: string;
}
