import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConversationContext, MessageRole


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    context_type: ConversationContext
    message: str


# --- Workout generation --------------------------------------------------------------------
# The AI-facing model is deliberately narrower than the API response: it can only pick an
# exercise_id from the candidate list it was given and describe sets/reps/notes — never a name,
# never anything else. app/services/ai_service.py resolves the id against the DB and drops (does
# not silently keep) any id the model didn't actually receive as a candidate.


class AIWorkoutExercisePick(BaseModel):
    exercise_id: str
    sets: int
    reps: str
    notes: str | None = None


class AIGeneratedWorkout(BaseModel):
    name: str
    exercises: list[AIWorkoutExercisePick]
    notes: str | None = None


class WorkoutGenerateRequest(BaseModel):
    equipment: list[str] = []
    duration_minutes: int | None = None
    focus: str | None = None  # free-text, e.g. "push day", "legs", "full body"


class GeneratedExerciseOut(BaseModel):
    exercise_id: uuid.UUID
    name: str
    muscle: str
    sets: int
    reps: str
    notes: str | None = None


class GeneratedWorkoutOut(BaseModel):
    name: str
    exercises: list[GeneratedExerciseOut]
    notes: str | None = None


# --- Food photo analysis --------------------------------------------------------------------
# Deliberately returns the same shape POST /nutrition/log expects (FoodLogItemIn) rather than
# writing a food log itself — an AI estimate is reviewed/edited by the user before it becomes a
# real logged entry, never auto-saved (spec.md §61: label estimates as approximate).


class AIFoodItemPick(BaseModel):
    name: str
    estimated_grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float


class AIFoodAnalysisResult(BaseModel):
    items: list[AIFoodItemPick]


class FoodAnalysisRequest(BaseModel):
    image_url: str
