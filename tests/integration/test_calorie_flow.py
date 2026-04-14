import pytest

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
from src.domain.models.meal_state import MealState


def setup_engine():
    return NutritionOrchestrator()


def test_single_item_calorie_flow():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple 200g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert response.total_calories == 104.0
    assert response.matched_items == 1
    assert len(response.items) == 1

    assert meal_state.total_calories == 104.0


def test_two_items_calorie_flow():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple 200g and banana 100g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert response.matched_items == 2
    assert response.total_calories == pytest.approx(193.0)

    assert meal_state.total_calories == pytest.approx(193.0)


def test_multi_item_without_and():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple 200g banana 100g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.matched_items == 2
    assert response.total_calories == pytest.approx(193.0)


def test_partial_match_with_unknown_food():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple 200g xyz 100g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.total_items == 2
    assert response.matched_items == 1
    assert response.total_calories == pytest.approx(104.0)


def test_typo_input_appl():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "appl 200g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert response.matched_items == 1
    assert response.total_calories == pytest.approx(104.0)


def test_compact_input_apple200g():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple200g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.matched_items == 1
    assert response.total_calories == pytest.approx(104.0)


def test_meal_memory_accumulates():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    engine.run("banana 100g", [], [], meal_state, [])

    assert meal_state.total_calories == pytest.approx(193.0)
    assert len(meal_state.items) == 2


def test_total_query_returns_meal_total():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])

    response = engine.run(
        "what is the total now?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert "total" in response.final_message.lower()
    assert meal_state.total_calories == pytest.approx(104.0)


def test_clear_meal_command():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])

    response = engine.run(
        "clear meal",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert meal_state.total_calories == 0
    assert len(meal_state.items) == 0


def test_remove_item_command():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])

    response = engine.run(
        "remove apple",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert meal_state.total_calories == 0
    assert len(meal_state.items) == 0


def test_repeat_detection_prevents_duplicate():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    response = engine.run("apple 200g", [], [], meal_state, [])

    assert len(meal_state.items) == 1  # should NOT duplicate
    assert "already" in response.final_message.lower()


def test_mixed_valid_and_invalid_inputs():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "apple 200g banana 100g xyz milk 200g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.total_items == 4
    assert response.matched_items >= 3
    assert meal_state.total_calories > 0


def test_large_input_stability():
    engine = setup_engine()
    meal_state = MealState()

    text = "apple 200g banana 100g milk 200g rice 150g oats 40g"

    response = engine.run(
        text,
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.matched_items >= 4
    assert meal_state.total_calories > 0