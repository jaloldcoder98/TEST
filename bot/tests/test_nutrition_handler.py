"""handlers.nutrition: the /logmeal FSM (meal type -> name -> grams -> calories -> protein ->
carbs -> fat) and the numeric-input helper it's built on."""

from __future__ import annotations

import handlers.nutrition as nutrition
from states import LogFood
from tests.conftest import make_callback, make_message


async def test_ask_number_parses_a_valid_number_and_advances_state(state):
    message = make_message(text="42.5")
    advanced = await nutrition._ask_number(message, state, "grams", LogFood.calories, "nutrition.ask_calories")

    assert advanced is True
    assert (await state.get_data())["grams"] == 42.5
    assert await state.get_state() == LogFood.calories
    assert message.calls == [{"text": nutrition.t("nutrition.ask_calories", "uz"), "reply_markup": None}]


async def test_ask_number_accepts_a_comma_decimal_separator(state):
    message = make_message(text="12,5")
    await nutrition._ask_number(message, state, "grams", None, "unused")
    assert (await state.get_data())["grams"] == 12.5


async def test_ask_number_rejects_non_numeric_input_without_advancing(state):
    message = make_message(text="not a number")
    advanced = await nutrition._ask_number(message, state, "grams", LogFood.calories, "nutrition.ask_calories")

    assert advanced is False
    assert await state.get_data() == {}
    assert await state.get_state() is None  # never advanced
    assert message.texts == [nutrition.t("invalid_number", "uz")]


async def test_ask_number_with_no_next_state_just_stores_the_value(state):
    # LogFood.fat is the last field — there's nothing to advance to.
    message = make_message(text="5")
    advanced = await nutrition._ask_number(message, state, "fat", None, "unused")
    assert advanced is True
    assert await state.get_state() is None


async def test_meal_type_selection_stores_type_and_prompts_for_name(state):
    callback = make_callback("meal:lunch")
    await nutrition.on_meal_type_selected(callback, state)

    assert (await state.get_data())["meal_type"] == "lunch"
    assert await state.get_state() == LogFood.name
    assert callback.message.texts == [nutrition.t("nutrition.ask_name", "uz")]


async def test_receive_food_name_stores_stripped_name_and_advances(state):
    message = make_message(text="  Grilled chicken  ")
    await nutrition.receive_food_name(message, state)

    assert (await state.get_data())["name"] == "Grilled chicken"
    assert await state.get_state() == LogFood.grams


async def test_nutrition_menu_shows_target_and_remaining_when_set(state, monkeypatch):
    async def fake_today_nutrition(token):
        return {
            "total_calories": 1200,
            "calorie_target": 2000,
            "remaining_calories": 800,
            "logs": [{"meal_type": "breakfast"}],
        }

    monkeypatch.setattr(nutrition.backend, "today_nutrition", fake_today_nutrition)
    monkeypatch.setattr(nutrition.backend, "telegram_auth", _fake_telegram_auth)

    message = make_message()
    await nutrition.nutrition_menu(message)

    text = message.texts[0]
    assert "1200" in text
    assert "800" in text and "2000" in text


async def test_nutrition_menu_shows_empty_state_when_nothing_logged(state, monkeypatch):
    async def fake_today_nutrition(token):
        return {"total_calories": 0, "calorie_target": None, "remaining_calories": None, "logs": []}

    monkeypatch.setattr(nutrition.backend, "today_nutrition", fake_today_nutrition)
    monkeypatch.setattr(nutrition.backend, "telegram_auth", _fake_telegram_auth)

    message = make_message()
    await nutrition.nutrition_menu(message)

    text = message.texts[0]
    assert nutrition.t("nutrition.today_no_target", "uz") in text
    assert nutrition.t("nutrition.today_empty", "uz") in text


async def _fake_telegram_auth(telegram_id, chat_id, username, first_name, language):
    return {"access_token": "fake-access", "refresh_token": "fake-refresh"}
