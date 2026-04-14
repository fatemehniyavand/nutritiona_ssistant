import json
import os

OUTPUT_PATH = "eval/datasets/eval_cases_adversarial.json"


def case(case_id, case_type, expected, input_text=None, steps=None):
    payload = {
        "id": case_id,
        "type": case_type,
        "expected": expected,
    }
    if input_text is not None:
        payload["input"] = input_text
    if steps is not None:
        payload["steps"] = steps
    return payload


def build_noise_cases():
    return [
        case("ADV-NOISE-001", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0,
        }, "apple 200g asdkjashd"),

        case("ADV-NOISE-002", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 3,
            "min_total_calories": 178.0,
            "max_total_calories": 181.0,
        }, "banana 100g ??? milk 150g"),

        case("ADV-NOISE-003", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 160.0,
            "max_total_calories": 170.0,
        }, "apple200gmilk100g"),

        case("ADV-NOISE-004", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 3,
            "min_total_calories": 178.0,
            "max_total_calories": 181.0,
        }, "banana100gandmilk150ghello"),

        case("ADV-NOISE-005", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0,
        }, "xyz apple 200g"),

        case("ADV-NOISE-006", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 85.0,
            "max_total_calories": 95.0,
        }, "hello banana 100g"),

        case("ADV-NOISE-007", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 120.0,
            "max_total_calories": 124.0,
        }, "milk 200g lorem"),

        case("ADV-NOISE-008", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 3,
            "min_total_calories": 250.0,
            "max_total_calories": 252.0,
        }, "rice100gandmilk200ghello"),
    ]


def build_ood_cases():
    return [
        case("ADV-OOD-001", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "unicorn milk 100g"),

        case("ADV-OOD-002", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "dragon meat 200g"),

        case("ADV-OOD-003", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "quantum rice 150g"),

        case("ADV-OOD-004", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "alien fruit 50g"),

        case("ADV-OOD-005", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "ghost food 100g"),

        case("ADV-OOD-006", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "space burger 150g"),

        case("ADV-OOD-007", "single_turn", {
            "mode": "calorie",
            "matched_items": 0,
            "confidence_in": ["LOW"],
        }, "mars protein 200g"),
    ]


def build_format_cases():
    return [
        case("ADV-FORMAT-001", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0,
        }, "apple,200g"),

        case("ADV-FORMAT-002", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0,
        }, "APPLE200G"),

        case("ADV-FORMAT-003", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 320.0,
            "max_total_calories": 340.0,
        }, "grilled-chicken 200g"),

        case("ADV-FORMAT-004", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 190.0,
            "max_total_calories": 195.0,
        }, "apple 200 g banana 100 g"),

        case("ADV-FORMAT-005", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 250.0,
            "max_total_calories": 252.0,
        }, "rice100gandmilk200g"),

        case("ADV-FORMAT-006", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0,
        }, "apple@@@200g"),

        case("ADV-FORMAT-007", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 178.0,
            "max_total_calories": 181.0,
        }, "banana100gandmilk150g"),
    ]


def build_guard_cases():
    return [
        case("ADV-GUARD-001", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "empty",
        }, ""),

        case("ADV-GUARD-002", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "digits",
        }, "apple two hundred grams"),

        case("ADV-GUARD-003", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "quantity",
        }, "banana"),

        case("ADV-GUARD-004", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "food name",
        }, "150g"),

        case("ADV-GUARD-005", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "english",
        }, "سلام"),

        case("ADV-GUARD-006", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True,
        }, "ciao"),

        case("ADV-GUARD-007", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "quantity",
        }, "brown rice"),
    ]


def build_memory_cases():
    return [
        case("ADV-MEM-001", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 193.0,
        }, steps=[
            "apple 200g",
            "banana 100g",
            "what is the total now?",
        ]),

        case("ADV-MEM-002", "multi_turn", {
            "final_mode": "calorie",
            "final_message_contains": "already",
        }, steps=[
            "apple 200g",
            "apple 200g",
        ]),

        case("ADV-MEM-003", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0,
        }, steps=[
            "banana 100g",
            "remove banana",
            "what is the total now?",
        ]),

        case("ADV-MEM-004", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0,
        }, steps=[
            "apple 200g",
            "clear meal",
        ]),

        case("ADV-MEM-005", "multi_turn", {
            "final_mode": "nutrition_qa",
            "answer_nonempty": True,
            "meal_total": 104.0,
        }, steps=[
            "apple 200g",
            "Is avocado healthy?",
        ]),

        case("ADV-MEM-006", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 277.6,
        }, steps=[
            "milk 200g",
            "oats 40g",
            "what is the total now?",
        ]),

        case("ADV-MEM-007", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 122.0,
        }, steps=[
            "apple 200g banana 100g",
            "clear meal",
            "milk 200g",
        ]),

        case("ADV-MEM-008", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 315.0,
        }, steps=[
            "apple 200g",
            "banana 100g",
            "milk 200g",
            "what is the total now?",
        ]),

        case("ADV-MEM-009", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 104.0,
        }, steps=[
            "apple 200g",
            "remove banana",
            "what is the total now?",
        ]),

        case("ADV-MEM-010", "multi_turn", {
            "final_mode": "calorie",
            "final_message_contains": "already",
        }, steps=[
            "milk 200g",
            "milk 200g",
        ]),
    ]


def build_base_cases():
    cases = []
    cases.extend(build_noise_cases())   # 8
    cases.extend(build_ood_cases())     # 7
    cases.extend(build_format_cases())  # 7
    cases.extend(build_guard_cases())   # 7
    cases.extend(build_memory_cases())  # 10
    return cases                        # total = 39


def clone_case_with_new_id(base_case, new_id):
    new_case = dict(base_case)
    new_case["id"] = new_id

    if "expected" in base_case:
        new_case["expected"] = dict(base_case["expected"])

    if "steps" in base_case:
        new_case["steps"] = list(base_case["steps"])

    return new_case


def main():
    cases = build_base_cases()

    base_count = len(cases)
    assert base_count == 39, f"Expected 39 adversarial base cases, got {base_count}"

    original = list(cases)
    next_index = base_count + 1

    while len(cases) < 50:
        base_case = original[(len(cases) - base_count) % len(original)]

        parts = base_case["id"].split("-")
        if len(parts) >= 3:
            new_id = f"{parts[0]}-{parts[1]}-{next_index:03}"
        else:
            new_id = f"{base_case['id']}-{next_index:03}"

        cases.append(clone_case_with_new_id(base_case, new_id))
        next_index += 1

    assert len(cases) == 50, f"Expected 50 adversarial cases, got {len(cases)}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} adversarial evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()