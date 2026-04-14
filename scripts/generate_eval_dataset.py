import json
import os


OUTPUT_PATH = "eval/datasets/eval_cases.json"


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


def main():
    cases = []

    # -------------------------------------------------
    # 1) Single-turn calorie cases (30)
    # -------------------------------------------------
    cases.extend([
        case("CAL-001", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 104.0
        }, "apple 200g"),

        case("CAL-002", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 89.0
        }, "banana 100g"),

        case("CAL-003", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 122.0
        }, "milk 200g"),

        case("CAL-004", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 195.0
        }, "rice 150g"),

        case("CAL-005", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 166.5
        }, "brown rice 150g"),

        case("CAL-006", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 330.0
        }, "chicken 200g"),

        case("CAL-007", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 330.0
        }, "grilled chicken 200g"),

        case("CAL-008", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 155.0
        }, "egg 100g"),

        case("CAL-009", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 160.0
        }, "avocado 100g"),

        case("CAL-010", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 155.6
        }, "oats 40g"),

        case("CAL-011", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 265.0
        }, "bread 100g"),

        case("CAL-012", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 52.0
        }, "apple 100g"),

        case("CAL-013", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 178.0
        }, "banana 200g"),

        case("CAL-014", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 61.0
        }, "milk 100g"),

        case("CAL-015", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 130.0
        }, "rice 100g"),

        case("CAL-016", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 222.0
        }, "brown rice 200g"),

        case("CAL-017", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 165.0
        }, "chicken 100g"),

        case("CAL-018", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 232.5
        }, "egg 150g"),

        case("CAL-019", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 80.0
        }, "avocado 50g"),

        case("CAL-020", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 389.0
        }, "oats 100g"),

        case("CAL-021", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 397.5
        }, "bread 150g"),

        case("CAL-022", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "appl 200g"),

        case("CAL-023", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 85.0,
            "max_total_calories": 95.0
        }, "bananna 100g"),

        case("CAL-024", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 150.0,
            "max_total_calories": 170.0
        }, "avocad 100g"),

        case("CAL-025", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 260.0,
            "max_total_calories": 270.0
        }, "bred 100g"),

        case("CAL-026", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 320.0,
            "max_total_calories": 340.0
        }, "grilled chiken 200g"),

        case("CAL-027", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 104.0
        }, "apple200g"),

        case("CAL-028", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 160.0,
            "max_total_calories": 170.0
        }, "brownrice150g"),

        case("CAL-029", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 320.0,
            "max_total_calories": 340.0
        }, "grilledchicken200g"),

        case("CAL-030", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 104.0
        }, "apple,200g"),
    ])

    # -------------------------------------------------
    # 2) Multi-item calorie cases (25)
    # -------------------------------------------------
    cases.extend([
        case("MUL-001", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 193.0
        }, "apple 200g and banana 100g"),

        case("MUL-002", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 299.0
        }, "apple 200g rice 150g"),

        case("MUL-003", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 277.6
        }, "milk 200g plus oats 40g"),

        case("MUL-004", "single_turn", {
            "mode": "calorie",
            "matched_items": 3,
            "total_items": 3,
            "total_calories": 315.0
        }, "apple 200g banana 100g milk 200g"),

        case("MUL-005", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 420.0,
            "max_total_calories": 440.0
        }, "chicken 100g bread 100g"),

        case("MUL-006", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 205.0,
            "max_total_calories": 215.0
        }, "rice 100g avocado 50g"),

        case("MUL-007", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 300.0,
            "max_total_calories": 310.0
        }, "egg 100g milk 250g"),

        case("MUL-008", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 240.0,
            "max_total_calories": 245.0
        }, "banana 50g bread 75g"),

        case("MUL-009", "single_turn", {
            "mode": "calorie",
            "matched_items": 3,
            "total_items": 3,
            "min_total_calories": 540.0,
            "max_total_calories": 560.0
        }, "apple 100g brown rice 150g chicken 200g"),

        case("MUL-010", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 164.0,
            "max_total_calories": 167.0
        }, "oats 40g and milk 16g"),

        case("MUL-011", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 290.0,
            "max_total_calories": 305.0
        }, "apple200grice150g"),

        case("MUL-012", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 193.0
        }, "apple 200 g banana 100 g"),

        case("MUL-013", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 178.0,
            "max_total_calories": 183.0
        }, "banana100gandmilk150g"),

        case("MUL-014", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 355.0,
            "max_total_calories": 362.0
        }, "avocado 100g bread 75g"),

        case("MUL-015", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 520.0,
            "max_total_calories": 526.0
        }, "rice 200g chicken 160g"),

        case("MUL-016", "single_turn", {
            "mode": "calorie",
            "matched_items": 3,
            "total_items": 3,
            "min_total_calories": 295.0,
            "max_total_calories": 301.0
        }, "apple 100g egg 100g milk 150g"),

        case("MUL-017", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 650.0,
            "max_total_calories": 660.0
        }, "oats 100g bread 100g"),

        case("MUL-018", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 130.0,
            "max_total_calories": 135.0
        }, "apple 100g avocado 50g"),

        case("MUL-019", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 236.0,
            "max_total_calories": 242.0
        }, "banana 50g egg 125g"),

        case("MUL-020", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 405.0,
            "max_total_calories": 412.0
        }, "bread 50g brown rice 250g"),

        case("MUL-021", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "min_total_calories": 268.0,
            "max_total_calories": 272.0
        }, "rice100gandmilk230g"),

        case("MUL-022", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 193.0
        }, "add apple 200g and banana 100g"),

        case("MUL-023", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 277.6
        }, "with milk 200g plus oats 40g"),

        case("MUL-024", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 2,
            "total_calories": 299.0
        }, "apple 200g and rice 150g"),

        case("MUL-025", "single_turn", {
            "mode": "calorie",
            "matched_items": 3,
            "total_items": 3,
            "min_total_calories": 338.0,
            "max_total_calories": 343.0
        }, "banana 100g rice 100g milk 200g"),
    ])

    # -------------------------------------------------
    # 3) Guard / invalid / robustness cases (20)
    # -------------------------------------------------
    cases.extend([
        case("GRD-001", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "empty"
        }, ""),

        case("GRD-002", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "empty"
        }, "   "),

        case("GRD-003", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "english"
        }, "سلام"),

        case("GRD-004", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "food name"
        }, "200g"),

        case("GRD-005", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "quantity"
        }, "apple"),

        case("GRD-006", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "digits"
        }, "apple two hundred grams"),

        case("GRD-007", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "hello world"),

        case("GRD-008", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "please apple 200g"),

        case("GRD-009", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "hello apple 200g xyz"),

        case("GRD-010", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "apple 200g xyz"),

        case("GRD-011", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 2,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "xyz apple 200g"),

        case("GRD-012", "single_turn", {
            "mode": "calorie",
            "matched_items": 2,
            "total_items": 3,
            "min_total_calories": 290.0,
            "max_total_calories": 305.0
        }, "apple 200g xyz rice 150g"),

        case("GRD-013", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 104.0
        }, "APPLE200G"),

        case("GRD-014", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "total_calories": 104.0
        }, "apple@@@200g"),

        case("GRD-015", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "total_items": 1,
            "min_total_calories": 320.0,
            "max_total_calories": 340.0
        }, "grilled-chicken 200g"),

        case("GRD-016", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "ciao"),

        case("GRD-017", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "quantity"
        }, "brown rice"),

        case("GRD-018", "single_turn", {
            "mode": "nutrition_qa",
            "answer_contains": "food name"
        }, "150 grams"),

        case("GRD-019", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "apple 200 grams"),

        case("GRD-020", "single_turn", {
            "mode": "calorie",
            "matched_items": 1,
            "min_total_calories": 100.0,
            "max_total_calories": 110.0
        }, "apple 200 g"),
    ])

    # -------------------------------------------------
    # 4) Meal memory and command cases (15)
    # -------------------------------------------------
    cases.extend([
        case("MEM-001", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 104.0
        }, steps=["apple 200g", "what is the total now?"]),

        case("MEM-002", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 193.0
        }, steps=["apple 200g", "banana 100g", "what is the total now?"]),

        case("MEM-003", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0
        }, steps=["apple 200g", "remove apple"]),

        case("MEM-004", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0
        }, steps=["apple 200g", "banana 100g", "clear meal"]),

        case("MEM-005", "multi_turn", {
            "final_mode": "calorie",
            "final_message_contains": "already"
        }, steps=["apple 200g", "apple 200g"]),

        case("MEM-006", "multi_turn", {
            "final_mode": "calorie",
            "final_message_contains": "already",
            "meal_total": 193.0
        }, steps=["apple 200g", "banana 100g", "apple 200g"]),

        case("MEM-007", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0
        }, steps=["banana 100g", "remove banana", "what is the total now?"]),

        case("MEM-008", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 277.6
        }, steps=["milk 200g", "oats 40g", "what is the total now?"]),

        case("MEM-009", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 122.0
        }, steps=["apple 200g banana 100g", "clear meal", "milk 200g"]),

        case("MEM-010", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 315.0
        }, steps=["apple 200g", "banana 100g", "milk 200g", "what is the total now?"]),

        case("MEM-011", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 104.0
        }, steps=["apple 200g", "remove banana", "what is the total now?"]),

        case("MEM-012", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 0.0
        }, steps=["clear meal"]),

        case("MEM-013", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 193.0
        }, steps=["apple 200g and banana 100g", "what is the total now?"]),

        case("MEM-014", "multi_turn", {
            "final_mode": "calorie",
            "final_message_contains": "already"
        }, steps=["milk 200g", "milk 200g"]),

        case("MEM-015", "multi_turn", {
            "final_mode": "calorie",
            "meal_total": 341.0
        }, steps=["banana 100g rice 100g milk 200g", "what is the total now?"]),
    ])

    # -------------------------------------------------
    # 5) QA cases (10)
    # -------------------------------------------------
    cases.extend([
        case("QA-001", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "What are good sources of protein?"),

        case("QA-002", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "Is avocado healthy?"),

        case("QA-003", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "Is rice good for weight loss?"),

        case("QA-004", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "What are healthy breakfast ideas?"),

        case("QA-005", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "Is milk good for bones?"),

        case("QA-006", "multi_turn", {
            "final_mode": "nutrition_qa",
            "final_message_contains": "as i told you before"
        }, steps=["Is avocado healthy?", "Is avocado healthy?"]),

        case("QA-007", "multi_turn", {
            "final_mode": "nutrition_qa",
            "answer_nonempty": True
        }, steps=["What are good sources of protein?", "What are good protein sources?"]),

        case("QA-008", "multi_turn", {
            "final_mode": "nutrition_qa",
            "answer_nonempty": True,
            "meal_total": 104.0
        }, steps=["apple 200g", "Is avocado healthy?"]),

        case("QA-009", "multi_turn", {
            "final_mode": "nutrition_qa",
            "answer_nonempty": True,
            "meal_total": 89.0
        }, steps=["banana 100g", "What are good sources of protein?"]),

        case("QA-010", "single_turn", {
            "mode": "nutrition_qa",
            "answer_nonempty": True
        }, "Is avocado healthy for breakfast?"),
    ])

    assert len(cases) == 100, f"Expected 100 cases, got {len(cases)}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()