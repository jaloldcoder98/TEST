from aiogram.fsm.state import State, StatesGroup


class LinkAccount(StatesGroup):
    username = State()
    password = State()


class NewWorkout(StatesGroup):
    name = State()
    searching = State()


class WorkoutSessionFlow(StatesGroup):
    awaiting_reps = State()
    awaiting_weight = State()


class LogFood(StatesGroup):
    name = State()
    grams = State()
    calories = State()
    protein = State()
    carbs = State()
    fat = State()


class LogWeight(StatesGroup):
    weight = State()


class ExerciseSearch(StatesGroup):
    query = State()
