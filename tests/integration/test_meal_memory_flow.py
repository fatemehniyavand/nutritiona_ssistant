import pytest

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
from src.domain.models.meal_state import MealState


def setup_engine():
    return NutritionOrchestrator()


def test_meal_memory_add_and_total_flow():
    engine = setup_engine()
    meal_state = MealState()

    # Step 1: add apple
    engine.run("apple 200g", [], [], meal_state, [])
    assert meal_state.total_calories == pytest.approx(104.0)
    assert len(meal_state.items) == 1

    # Step 2: add banana
    engine.run("banana 100g", [], [], meal_state, [])
    assert meal_state.total_calories == pytest.approx(193.0)
    assert len(meal_state.items) == 2

    # Step 3: query total
    response = engine.run(
        "what is the total now?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert "total" in response.final_message.lower()
    assert meal_state.total_calories == pytest.approx(193.0)


def test_remove_single_item_from_meal():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    engine.run("banana 100g", [], [], meal_state, [])

    response = engine.run(
        "remove apple",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert len(meal_state.items) == 1
    assert meal_state.items[0].food == "banana"
    assert meal_state.total_calories == pytest.approx(89.0)


def test_clear_meal_resets_state():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    engine.run("banana 100g", [], [], meal_state, [])

    response = engine.run(
        "clear meal",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert meal_state.total_calories == 0
    assert len(meal_state.items) == 0


def test_repeat_same_item_does_not_duplicate():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    response = engine.run("apple 200g", [], [], meal_state, [])

    assert len(meal_state.items) == 1
    assert "already" in response.final_message.lower()


def test_repeat_item_from_conversation_memory_not_auto_added():
    engine = setup_engine()
    meal_state = MealState()

    # First query (goes into conversation memory context externally)
    first = engine.run("apple 200g", [], [], meal_state, [])

    # Remove it
    engine.run("remove apple", [], [], meal_state, [])

    assert len(meal_state.items) == 0

    # Simulate conversation memory containing previous result
    conversation_memory = [
        {
            "kind": "calorie",
            "user_input": "apple 200g",
            "normalized_input": "apple 200g",
            "items": [
                {
                    "input_food": "apple",
                    "matched_food": "apple",
                    "grams": 200,
                    "calories": 104.0,
                    "kcal_per_100g": 52,
                }
            ],
        }
    ]

    response = engine.run(
        "apple 200g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )

    # Should NOT auto-add
    assert len(meal_state.items) == 0
    assert "not currently in your meal" in response.final_message.lower()


def test_add_after_repeat_from_memory():
    engine = setup_engine()
    meal_state = MealState()

    # simulate previous memory
    conversation_memory = [
        {
            "kind": "calorie",
            "user_input": "banana 100g",
            "normalized_input": "banana 100g",
            "items": [
                {
                    "input_food": "banana",
                    "matched_food": "banana",
                    "grams": 100,
                    "calories": 89.0,
                    "kcal_per_100g": 89,
                }
            ],
        }
    ]

    # first repeat response (not added)
    engine.run(
        "banana 100g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )

    assert len(meal_state.items) == 0

    # user explicitly adds it
    engine.run(
        "add banana 100g",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert len(meal_state.items) == 1
    assert meal_state.total_calories == pytest.approx(89.0)


def test_multiple_items_then_clear_then_add_again():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g banana 100g", [], [], meal_state, [])
    assert len(meal_state.items) == 2

    engine.run("clear meal", [], [], meal_state, [])
    assert len(meal_state.items) == 0

    engine.run("milk 200g", [], [], meal_state, [])
    assert len(meal_state.items) == 1
    assert meal_state.total_calories == pytest.approx(122.0)


def test_total_after_multiple_operations():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    engine.run("banana 100g", [], [], meal_state, [])
    engine.run("milk 200g", [], [], meal_state, [])

    response = engine.run(
        "what is the total now?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "calorie"
    assert meal_state.total_calories == pytest.approx(104 + 89 + 122)


def test_remove_non_existing_item_does_not_crash():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])

    response = engine.run(
        "remove banana",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert len(meal_state.items) == 1
    assert meal_state.total_calories == pytest.approx(104.0)


def test_clear_empty_meal_is_safe():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "clear meal",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert meal_state.total_calories == 0
    assert len(meal_state.items) == 0