import uuid

from pydantic import BaseModel


class LookupOut(BaseModel):
    slug: str
    count: int


class ExerciseSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    muscle: str
    body_part: str
    equipment: str
    category: str
    gif_url: str
    image_url: str | None
    is_favorited: bool = False


class ExerciseDetail(ExerciseSummary):
    secondary_muscles: list[str]
    instructions: list[str]
    source: str
    source_url: str | None
    is_machine_translated: bool


class PaginatedExercises(BaseModel):
    items: list[ExerciseSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
