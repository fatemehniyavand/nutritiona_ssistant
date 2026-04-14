import pytest

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
from src.domain.models.meal_state import MealState
from src.domain.models.conversation_memory import MemoryEntry


def setup_engine():
    return NutritionOrchestrator()


def test_basic_qa_question_returns_qa_mode():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "What are good sources of protein?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert hasattr(response, "answer")
    assert isinstance(response.answer, str)
    assert len(response.answer.strip()) > 0


def test_qa_does_not_modify_meal_memory():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "Is avocado healthy?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert meal_state.total_calories == 0
    assert len(meal_state.items) == 0


def test_exact_qa_repeat_from_conversation_memory():
    engine = setup_engine()
    meal_state = MealState()

    conversation_memory = [
        {
            "kind": "nutrition_qa",
            "user_input": "Is avocado healthy?",
            "normalized_input": "is avocado healthy",
            "answer": "Yes, avocado can be part of a healthy diet.",
            "confidence": "HIGH",
            "sources_used": ["nutrition_qna"],
            "retrieved_contexts": ["Avocado contains healthy fats and fiber."],
        }
    ]

    response = engine.run(
        "Is avocado healthy?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )

    assert response.mode == "nutrition_qa"
    assert "avocado" in response.answer.lower()
    assert "as i told you before" in response.final_message.lower()


def test_similar_qa_repeat_from_conversation_memory():
    engine = setup_engine()
    meal_state = MealState()

    conversation_memory = [
        {
            "kind": "nutrition_qa",
            "user_input": "Is avocado healthy?",
            "normalized_input": "is avocado healthy",
            "answer": "Yes, avocado can be part of a healthy diet.",
            "confidence": "HIGH",
            "sources_used": ["nutrition_qna"],
            "retrieved_contexts": ["Avocado contains healthy fats and fiber."],
        }
    ]

    response = engine.run(
        "Is avocado good for health?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )

    assert response.mode == "nutrition_qa"
    assert len(response.answer.strip()) > 0
    assert "as i told you before" in response.final_message.lower()


def test_qa_repeat_from_semantic_memory_entries():
    engine = setup_engine()
    meal_state = MealState()

    memory_entries = [
        MemoryEntry(
            question="what are good sources of protein",
            answer="Good protein sources include eggs, chicken, fish, beans, and yogurt.",
            mode="nutrition_qa",
            confidence="HIGH",
            sources_used=["nutrition_qna"],
        )
    ]

    response = engine.run(
        "What are good protein sources?",
        history=[],
        memory_entries=memory_entries,
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert len(response.answer.strip()) > 0
    assert (
        "semantic memory" in response.final_message.lower()
        or "as i told you before" in response.final_message.lower()
    )


def test_qa_question_after_calorie_queries_still_returns_qa():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    engine.run("banana 100g", [], [], meal_state, [])

    response = engine.run(
        "Is rice good for weight loss?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert len(response.answer.strip()) > 0
    assert meal_state.total_calories > 0  # meal memory should remain intact


def test_qa_response_has_confidence_field():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "Is avocado healthy?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert hasattr(response, "confidence")
    assert response.confidence in {"LOW", "MEDIUM", "HIGH"}


def test_qa_response_contains_sources_fields_even_if_empty():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "What are good sources of protein?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert hasattr(response, "sources_used")
    assert hasattr(response, "retrieved_contexts")
    assert isinstance(response.sources_used, list)
    assert isinstance(response.retrieved_contexts, list)


def test_non_food_general_nutrition_question_goes_to_qa():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "What are healthy breakfast ideas?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert len(response.answer.strip()) > 0


def test_qa_repeat_ignores_previous_calorie_entries():
    engine = setup_engine()
    meal_state = MealState()

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
        "Is avocado healthy?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )

    assert response.mode == "nutrition_qa"
    assert "as i told you before" not in response.final_message.lower()


def test_food_like_question_should_not_become_calorie_mode():
    engine = setup_engine()
    meal_state = MealState()

    response = engine.run(
        "Is avocado healthy for breakfast?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"


def test_qa_query_with_existing_meal_memory_keeps_meal_unchanged():
    engine = setup_engine()
    meal_state = MealState()

    engine.run("apple 200g", [], [], meal_state, [])
    before_total = meal_state.total_calories
    before_len = len(meal_state.items)

    response = engine.run(
        "What are good sources of protein?",
        history=[],
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=[],
    )

    assert response.mode == "nutrition_qa"
    assert meal_state.total_calories == before_total
    assert len(meal_state.items) == before_len