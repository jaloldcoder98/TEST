"""Every fixed-choice field in the schema, as Python enums (mapped to native Postgres enum
types). Kept in one file so `docs/DATABASE.md`'s enum lists and the actual schema never
silently drift — if you add a value here, update that doc in the same change.
"""

import enum


class Language(str, enum.Enum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class Goal(str, enum.Enum):
    LOSE_WEIGHT = "lose_weight"
    MAINTAIN_WEIGHT = "maintain_weight"
    GAIN_MUSCLE = "gain_muscle"
    GAIN_WEIGHT = "gain_weight"
    IMPROVE_FITNESS = "improve_fitness"
    STRENGTH = "strength"


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTRA_ACTIVE = "extra_active"


class WorkoutCategory(str, enum.Enum):
    PUSH = "push"
    PULL = "pull"
    LEGS = "legs"
    UPPER = "upper"
    LOWER = "lower"
    FULL_BODY = "full_body"
    CUSTOM = "custom"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecordType(str, enum.Enum):
    MAX_WEIGHT = "max_weight"
    MAX_REPS = "max_reps"
    MAX_VOLUME = "max_volume"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class FoodSource(str, enum.Enum):
    MANUAL = "manual"
    USDA = "usda"
    AI_SUGGESTED = "ai_suggested"


class ConversationContext(str, enum.Enum):
    FITNESS_COACH = "fitness_coach"
    NUTRITION_COACH = "nutrition_coach"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class FavoritableType(str, enum.Enum):
    EXERCISE = "exercise"
    WORKOUT = "workout"
    FOOD_ITEM = "food_item"
