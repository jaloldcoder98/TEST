"""Import every model here so `Base.metadata` is fully populated for Alembic autogenerate —
`alembic/env.py` imports this module, nothing else, to see the whole schema."""

from app.models.ai import AIConversation, AIMessage
from app.models.base import Base
from app.models.exercise import BodyPart, Category, Equipment, Exercise, ExerciseTranslation, Muscle
from app.models.nutrition import FoodItem, FoodLog, FoodLogItem, NutritionDaily
from app.models.progress import BodyMeasurement
from app.models.user import AuditLog, Favorite, Notification, RefreshToken, TelegramUser, User, UserProfile
from app.models.workout import (
    PersonalRecord,
    Workout,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutTemplate,
)

__all__ = [
    "Base",
    "AIConversation",
    "AIMessage",
    "BodyPart",
    "Category",
    "Equipment",
    "Exercise",
    "ExerciseTranslation",
    "Muscle",
    "FoodItem",
    "FoodLog",
    "FoodLogItem",
    "NutritionDaily",
    "BodyMeasurement",
    "AuditLog",
    "Favorite",
    "Notification",
    "RefreshToken",
    "TelegramUser",
    "User",
    "UserProfile",
    "PersonalRecord",
    "Workout",
    "WorkoutExercise",
    "WorkoutSession",
    "WorkoutSet",
    "WorkoutTemplate",
]
