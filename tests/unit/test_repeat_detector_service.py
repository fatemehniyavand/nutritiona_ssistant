from types import SimpleNamespace

from src.application.services.repeat_detector_service import RepeatDetectorService


def make_meal_item(food, grams, calories=100, kcal=50):
    return SimpleNamespace(
        food=food,
        grams=grams,
        calories=calories,
        kcal_per_100g=kcal,
    )


def make_meal_state(items):
    return SimpleNamespace(items=items)


def make_calorie_memory_entry(food, grams, calories=100, kcal=50):
    return {
        "kind": "calorie",
        "items": [
            {
                "input_food": food,
                "matched_food": food,
                "grams": grams,
                "calories": calories,
                "kcal_per_100g": kcal,
            }
        ],
    }


def make_qa_memory_entry(question, answer="ok"):
    return {
        "kind": "nutrition_qa",
        "user_input": question,
        "answer": answer,
    }


def test_repeat_detected_in_meal_memory_exact():
    service = RepeatDetectorService()

    meal_state = make_meal_state([
        make_meal_item("apple", 200, 104, 52)
    ])

    result = service.find_calorie_repeat(
        input_food="apple",
        matched_food="apple",
        grams=200,
        meal_state=meal_state,
    )

    assert result["found"] is True
    assert result["repeat_type"] == "meal_memory"


def test_repeat_detected_in_meal_memory_with_typo():
    service = RepeatDetectorService()

    meal_state = make_meal_state([
        make_meal_item("apple", 200)
    ])

    result = service.find_calorie_repeat(
        input_food="appl",
        matched_food="apple",
        grams=200,
        meal_state=meal_state,
    )

    assert result["found"] is True
    assert result["repeat_type"] == "meal_memory"


def test_no_repeat_if_different_grams():
    service = RepeatDetectorService()

    meal_state = make_meal_state([
        make_meal_item("apple", 200)
    ])

    result = service.find_calorie_repeat(
        input_food="apple",
        matched_food="apple",
        grams=150,
        meal_state=meal_state,
    )

    assert result["found"] is False


def test_repeat_detected_in_conversation_memory():
    service = RepeatDetectorService()

    conversation_memory = [
        make_calorie_memory_entry("banana", 100)
    ]

    result = service.find_calorie_repeat(
        input_food="banana",
        matched_food="banana",
        grams=100,
        meal_state=make_meal_state([]),
        conversation_memory=conversation_memory,
    )

    assert result["found"] is True
    assert result["repeat_type"] == "conversation_memory"


def test_no_repeat_when_food_is_different():
    service = RepeatDetectorService()

    meal_state = make_meal_state([
        make_meal_item("apple", 200)
    ])

    result = service.find_calorie_repeat(
        input_food="banana",
        matched_food="banana",
        grams=200,
        meal_state=meal_state,
    )

    assert result["found"] is False


def test_qa_exact_repeat_detected():
    service = RepeatDetectorService()

    memory = [
        make_qa_memory_entry("Is avocado healthy?")
    ]

    result = service.find_qa_repeat(
        question_text="Is avocado healthy?",
        conversation_memory=memory,
    )

    assert result["found"] is True
    assert result["similarity"] == 1.0


def test_qa_fuzzy_repeat_detected():
    service = RepeatDetectorService()

    memory = [
        make_qa_memory_entry("Is avocado healthy?")
    ]

    result = service.find_qa_repeat(
        question_text="Is avocado good for health?",
        conversation_memory=memory,
        threshold=0.7,
    )

    assert result["found"] is True
    assert result["similarity"] >= 0.7


def test_qa_no_repeat_when_different_question():
    service = RepeatDetectorService()

    memory = [
        make_qa_memory_entry("Is avocado healthy?")
    ]

    result = service.find_qa_repeat(
        question_text="What are good sources of protein?",
        conversation_memory=memory,
    )

    assert result["found"] is False


def test_qa_repeat_ignores_non_qa_entries():
    service = RepeatDetectorService()

    memory = [
        make_calorie_memory_entry("apple", 200)
    ]

    result = service.find_qa_repeat(
        question_text="Is avocado healthy?",
        conversation_memory=memory,
    )

    assert result["found"] is False


def test_empty_memory_returns_no_repeat():
    service = RepeatDetectorService()

    result = service.find_calorie_repeat(
        input_food="apple",
        matched_food="apple",
        grams=200,
        meal_state=make_meal_state([]),
        conversation_memory=[],
    )

    assert result["found"] is False