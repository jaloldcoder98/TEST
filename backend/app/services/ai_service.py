"""AI Coach, workout generation, nutrition Q&A, and food-photo analysis (Phase 7).

Every AI call goes through the AIProvider abstraction (app/ai/providers) — never the OpenAI SDK
directly — and every route depends on `get_provider()` returning non-None, so "no API key
configured" is a single, honest 503 AI_NOT_CONFIGURED rather than a crash or fake data
(spec.md §61: no mock data in production paths). Structured outputs (workout generation, food
analysis) are always validated against a Pydantic schema before use, and workout generation is
additionally grounded against the real exercise database: the model may only pick from a
candidate list it was given, and any id it returns that wasn't in that list is silently dropped,
never trusted (spec.md §51/§61 — never invent exercise ids).
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.ai.prompts.loader import load_prompt
from app.ai.providers.base import AIProvider
from app.ai.providers.factory import get_provider
from app.core.errors import AppError, NotFoundError
from app.models import AIConversation, AIMessage, Equipment, Exercise, FoodItem, User
from app.models.enums import ConversationContext, Language, MessageRole
from app.repositories.exercise_repository import pick_translation
from app.schemas.ai import (
    AIFoodAnalysisResult,
    AIGeneratedWorkout,
    ChatRequest,
    ChatResponse,
    FoodAnalysisRequest,
    GeneratedExerciseOut,
    GeneratedWorkoutOut,
    WorkoutGenerateRequest,
)

MAX_HISTORY_MESSAGES = 20
CANDIDATE_EXERCISE_POOL = 40


def _require_provider() -> AIProvider:
    provider = get_provider()
    if provider is None:
        raise AppError(
            "AI_NOT_CONFIGURED",
            "The AI assistant isn't available yet — no AI provider is configured on the server.",
            503,
        )
    return provider


async def _get_or_create_conversation(
    db: AsyncSession, user_id: uuid.UUID, context_type: ConversationContext, conversation_id: uuid.UUID | None
) -> AIConversation:
    if conversation_id is not None:
        result = await db.execute(
            select(AIConversation)
            .options(selectinload(AIConversation.messages))
            .where(AIConversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("CONVERSATION_NOT_FOUND", "Conversation not found")
        if conversation.user_id != user_id:
            raise AppError("FORBIDDEN", "This conversation belongs to another user", 403)
        return conversation

    conversation = AIConversation(user_id=user_id, context_type=context_type)
    db.add(conversation)
    await db.flush()
    # Seed the in-memory relationship state directly rather than assigning `conversation.messages =
    # []`: a normal assignment to a `back_populates` collection first loads the *current* value to
    # do backref bookkeeping/cascades, which needs IO and raises MissingGreenlet outside an
    # explicit await on an AsyncSession. `set_committed_value` marks the collection as already
    # loaded (empty, since this conversation is brand new) without touching the database.
    set_committed_value(conversation, "messages", [])
    return conversation


async def _append_message(
    db: AsyncSession, conversation: AIConversation, role: MessageRole, content: str, structured_data: dict | None = None
) -> AIMessage:
    message = AIMessage(conversation_id=conversation.id, role=role, content=content, structured_data=structured_data)
    db.add(message)
    await db.flush()
    # Keep the already-loaded `conversation.messages` collection in sync so `_history_payload` (and
    # any other in-request reader) sees this turn without needing another DB round trip.
    conversation.messages.append(message)
    return message


def _history_payload(conversation: AIConversation) -> list[dict[str, str]]:
    recent = conversation.messages[-MAX_HISTORY_MESSAGES:]
    payload = [{"role": m.role.value, "content": m.content} for m in recent]
    if conversation.summary:
        # Older turns are summarized rather than dropped or sent in full (docs/DATABASE.md /
        # spec.md §33) — prepended as context so the model isn't blind to what happened earlier.
        payload.insert(0, {"role": "user", "content": f"[Earlier conversation summary: {conversation.summary}]"})
    return payload


async def chat(db: AsyncSession, user: User, data: ChatRequest) -> ChatResponse:
    provider = _require_provider()
    conversation = await _get_or_create_conversation(db, user.id, ConversationContext.FITNESS_COACH, data.conversation_id)

    await _append_message(db, conversation, MessageRole.USER, data.message)
    reply = await provider.chat(load_prompt("coach"), _history_payload(conversation))
    await _append_message(db, conversation, MessageRole.ASSISTANT, reply)

    return ChatResponse(conversation_id=conversation.id, context_type=conversation.context_type, message=reply)


async def ask_nutrition(db: AsyncSession, user: User, data: ChatRequest) -> ChatResponse:
    provider = _require_provider()
    conversation = await _get_or_create_conversation(db, user.id, ConversationContext.NUTRITION_COACH, data.conversation_id)

    grounded_prompt = data.message
    known_foods = await _find_relevant_food_items(db, data.message)
    if known_foods:
        facts = "\n".join(
            f"- {f.name_en}: {f.calories_per_100g} kcal, {f.protein_g_per_100g}g protein, "
            f"{f.carbs_g_per_100g}g carbs, {f.fat_g_per_100g}g fat (per 100g)"
            for f in known_foods
        )
        grounded_prompt = f"{data.message}\n\n[Known foods from the app's database — use these numbers if relevant:\n{facts}]"

    await _append_message(db, conversation, MessageRole.USER, data.message)
    history = _history_payload(conversation)
    history[-1] = {"role": "user", "content": grounded_prompt}  # augment only what's sent, not what's stored
    reply = await provider.chat(load_prompt("nutrition_assistant"), history)
    await _append_message(db, conversation, MessageRole.ASSISTANT, reply)

    return ChatResponse(conversation_id=conversation.id, context_type=conversation.context_type, message=reply)


async def _find_relevant_food_items(db: AsyncSession, message: str, limit: int = 5) -> list[FoodItem]:
    words = [w for w in message.lower().split() if len(w) >= 4]
    if not words:
        return []
    conditions = [FoodItem.name_en.ilike(f"%{w}%") for w in words[:8]]
    result = await db.execute(select(FoodItem).where(or_(*conditions)).limit(limit))
    return list(result.scalars().all())


async def generate_workout(db: AsyncSession, user: User, data: WorkoutGenerateRequest) -> GeneratedWorkoutOut:
    provider = _require_provider()

    query = select(Exercise).options(
        selectinload(Exercise.muscle), selectinload(Exercise.equipment), selectinload(Exercise.translations)
    ).where(Exercise.is_active.is_(True))
    if data.equipment:
        query = query.where(Exercise.equipment.has(Equipment.slug.in_(data.equipment)))
    query = query.order_by(func.random()).limit(CANDIDATE_EXERCISE_POOL)
    candidates = list((await db.execute(query)).scalars().unique().all())
    if not candidates:
        raise AppError("NO_EXERCISES_AVAILABLE", "No exercises match the given equipment", 422)

    lang = user.language if isinstance(user.language, Language) else Language(user.language)
    by_id = {str(ex.id): ex for ex in candidates}
    candidate_lines = "\n".join(
        f"- id: {ex.id} | name: {pick_translation(ex, lang).name} | muscle: {ex.muscle.slug} | equipment: {ex.equipment.slug}"
        for ex in candidates
    )
    profile = user.profile
    context_lines = [
        f"Candidate exercises (pick only from this list):\n{candidate_lines}",
        f"Requested focus: {data.focus or 'not specified'}",
        f"Duration: {data.duration_minutes or 'not specified'} minutes",
    ]
    if profile:
        context_lines.append(
            f"User goal: {profile.goal.value if profile.goal else 'not specified'}, "
            f"experience: {profile.experience_level.value if profile.experience_level else 'not specified'}"
        )
    user_prompt = "\n\n".join(context_lines)

    try:
        result: AIGeneratedWorkout = await provider.structured(load_prompt("workout_generator"), user_prompt, AIGeneratedWorkout)
    except ValueError as exc:
        raise AppError("AI_INVALID_OUTPUT", "The AI assistant couldn't generate a valid workout. Try again.", 502) from exc

    resolved: list[GeneratedExerciseOut] = []
    for pick in result.exercises:
        exercise = by_id.get(pick.exercise_id)
        if exercise is None:
            # The model picked something outside the candidate list it was given — dropped, not
            # trusted, per the grounding rule in this module's docstring.
            continue
        resolved.append(
            GeneratedExerciseOut(
                exercise_id=exercise.id,
                name=pick_translation(exercise, lang).name,
                muscle=exercise.muscle.slug,
                sets=pick.sets,
                reps=pick.reps,
                notes=pick.notes,
            )
        )

    if not resolved:
        raise AppError(
            "AI_INVALID_OUTPUT", "The AI assistant didn't return any valid exercises. Try again.", 502
        )

    return GeneratedWorkoutOut(name=result.name, exercises=resolved, notes=result.notes)


async def analyze_food_image(data: FoodAnalysisRequest) -> AIFoodAnalysisResult:
    provider = _require_provider()
    try:
        return await provider.analyze_image(load_prompt("food_analysis"), data.image_url, AIFoodAnalysisResult)
    except ValueError as exc:
        raise AppError("AI_INVALID_OUTPUT", "The AI assistant couldn't analyze that photo. Try again.", 502) from exc
