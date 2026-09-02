# GYM Platform — Database Schema

PostgreSQL. SQLAlchemy 2.x models, versioned with Alembic. All primary keys are UUIDv4 unless
noted. All tables get `created_at`/`updated_at` (omitted below where obvious).

## Core tables

### users
`id, telegram_id (nullable, unique), email (nullable, unique), username (unique), password_hash
(nullable — null for Telegram-only accounts), first_name, last_name, language (uz|ru|en),
is_active, is_admin, created_at, updated_at`

### user_profiles (1:1 with users)
`user_id (FK, PK), date_of_birth, gender, height_cm, weight_kg, goal, experience_level,
activity_level, daily_calorie_target, protein_target_g, carbs_target_g, fat_target_g`

Enums — `goal`: lose_weight | maintain_weight | gain_muscle | gain_weight | improve_fitness |
strength. `experience_level`: beginner | intermediate | advanced. `activity_level`: sedentary |
lightly_active | moderately_active | very_active | extra_active.

### telegram_users
`id, user_id (FK), telegram_id (unique), chat_id, telegram_username, linked_at`

Kept separate from `users.telegram_id` so a web account and a Telegram identity can be linked
after the fact (spec §30 account-linking flow) without a schema change.

## Exercise catalog

### muscles / equipment / body_parts / categories (lookup tables)
`id, slug (unique), sort_order` — small reference tables rather than free-text enums, so the
admin panel (spec §38) can manage them without a migration.

### exercises
`id, external_id (unique, e.g. "biceps/barbell-curl"), slug (unique), muscle_id (FK),
body_part_id (FK), equipment_id (FK), category_id (FK), secondary_muscles (array of muscle_id,
or a join table `exercise_secondary_muscles` if we need queryability — see note), gif_url,
image_url (thumb), source (e.g. "exercisegymgifsdb"), source_url, is_active, created_at,
updated_at`

Note: `secondary_muscles` as a Postgres array is simplest and matches the source data shape
(list of muscle slugs); switch to a join table only if we need to filter/aggregate by secondary
muscle later — flag this as a Phase 3 implementation decision, not fixed here.

### exercise_translations
`id, exercise_id (FK), language (uz|ru|en), name, instructions (JSON array of strings),
description (nullable), is_machine_translated (bool), created_at, updated_at`
Unique on `(exercise_id, language)`.

## Workouts

### workout_templates
`id, name, description, category (push|pull|legs|upper|lower|full_body|custom), is_public,
created_by (FK users, nullable for system templates)`

### workouts
`id, user_id (FK), template_id (FK, nullable), name, description, day, duration_minutes,
created_at`

### workout_exercises
`id, workout_id (FK), exercise_id (FK), order, notes`

### workout_sessions
`id, user_id (FK), workout_id (FK), status (in_progress|paused|completed|cancelled),
started_at, finished_at, total_volume_kg, total_sets, total_reps, estimated_calories`

### workout_sets
`id, workout_session_id (FK) — logged against a *session*, not the static workout_exercise, so
history is immutable, workout_exercise_id (FK), set_number, reps, weight_kg, duration_seconds
(for timed exercises), rest_seconds, completed (bool), notes`

### personal_records
`id, user_id (FK), exercise_id (FK), record_type (max_weight|max_reps|max_volume), value,
achieved_at, workout_set_id (FK)` — derived/materialized on set completion rather than computed
on every read.

## Nutrition

### food_items (local nutrition database — spec §19: "do not rely exclusively on AI-generated
nutritional values")
`id, name_en, name_ru, name_uz, calories_per_100g, protein_g_per_100g, carbs_g_per_100g,
fat_g_per_100g, fiber_g_per_100g (nullable), source (manual|usda|ai_suggested), is_verified`

### food_logs
`id, user_id (FK), date, meal_type (breakfast|lunch|dinner|snack), description,
image_url (nullable), total_calories, protein_g, carbs_g, fat_g, ai_confidence (nullable),
created_at`

### food_log_items
`id, food_log_id (FK), food_item_id (FK, nullable — null if AI-identified item has no DB match
yet), name, estimated_grams, calories, protein_g, carbs_g, fat_g, confidence`

### nutrition_daily (materialized/rolled-up per user per day — avoids re-summing food_logs on
every dashboard load)
`id, user_id (FK), date, total_calories, protein_g, carbs_g, fat_g, remaining_calories`
Unique on `(user_id, date)`.

## Progress

### body_measurements
`id, user_id (FK), date, weight_kg, body_fat_pct, chest_cm, waist_cm, hips_cm, arms_cm,
thighs_cm, notes`

### progress_records
Optional narrower table if we want a unified timeline across weight/strength/volume for
dashboard charts rather than querying multiple tables — `id, user_id (FK), date, metric_type,
value` (generic key-value time series). Decide during Phase 3 whether `body_measurements` alone
covers this or both are needed.

## AI

### ai_conversations
`id, user_id (FK), context_type (fitness_coach|nutrition_coach), created_at, updated_at`

### ai_messages
`id, conversation_id (FK), role (user|assistant), content, structured_data (JSON, nullable —
e.g. a generated workout card), token_count, created_at`

Conversation summarization (spec §33) writes a periodic `summary` field onto
`ai_conversations` rather than deleting old `ai_messages`, so raw history is preserved for audit
while only the summary + recent N messages are sent to the model.

## Misc

- **favorites**: `id, user_id (FK), favoritable_type (exercise|workout|food_item), favoritable_id`
- **refresh_tokens**: `id, user_id (FK), token_hash, expires_at, revoked_at (nullable)`
- **notifications**: `id, user_id (FK), type, payload (JSON), read_at (nullable), created_at`
- **audit_logs**: `id, user_id (FK, nullable), action, entity_type, entity_id, metadata (JSON),
  created_at` — never logs passwords/tokens/images (spec §44).

## Relationships (summary)

```
User 1─1 UserProfile
User 1─N Workouts, FoodLogs, ProgressRecords/BodyMeasurements, AIConversations, Favorites
User 1─1 TelegramUser (nullable)
Workout 1─N WorkoutExercises
Exercise 1─N WorkoutExercises, 1─N ExerciseTranslations (one per language)
WorkoutSession 1─N WorkoutSets
AIConversation 1─N AIMessages
FoodLog 1─N FoodLogItems
```

## Indexes (Phase 3 checklist, spec §25/§40)

- `exercises`: btree on `muscle_id`, `equipment_id`, `body_part_id`, `category_id`; trigram
  (`pg_trgm`) index on translated `name` for fuzzy multilingual search.
- `workout_sets`, `food_logs`: btree on `(user_id, date)` / `(workout_session_id)` — these are
  the dashboard's hot paths.
- `exercise_translations`: unique `(exercise_id, language)`, index on `language`.
