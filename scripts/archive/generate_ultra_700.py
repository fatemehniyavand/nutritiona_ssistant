import json
import random

random.seed(42)

foods = [
    ("apple", 52), ("banana", 89), ("mango", 60),
    ("pineapple", 50), ("kiwi", 61), ("orange", 47),
    ("grapes", 69), ("pear", 57)
]

fake_foods = [
    "dragon meat", "robot soup", "alien fruit",
    "quantum bread", "cyber banana", "ghost milk"
]

def cal(food, grams, per100):
    return round((grams / 100) * per100)

data = []
i = 1

def next_id():
    global i
    val = f"ULTRA_{i:03}"
    i += 1
    return val

# ---------------------------
# 1. EXACT DECIMAL
# ---------------------------
for _ in range(50):
    f, c = random.choice(foods)
    g = random.choice([73, 137, 155.5, 212, 99])
    total = cal(f, g, c)
    data.append({
        "id": next_id(),
        "category": "CAL_EXACT_DECIMAL",
        "input": f"{f} {g}g",
        "expected_mode": "calorie_input",
        "expected_total_calories": total,
        "expected_matched_foods": [f],
        "must_contain": [f, str(int(total))]
    })

# ---------------------------
# 2. MULTI ITEM
# ---------------------------
for _ in range(50):
    f1, c1 = random.choice(foods)
    f2, c2 = random.choice(foods)
    g1 = random.choice([100, 150, 200])
    g2 = random.choice([50, 100])
    total = cal(f1, g1, c1) + cal(f2, g2, c2)

    data.append({
        "id": next_id(),
        "category": "CAL_MULTI",
        "input": f"{f1} {g1}g and {f2} {g2}g",
        "expected_mode": "calorie_input",
        "expected_total_calories": total,
        "must_contain": [str(total)]
    })

# ---------------------------
# 3. NOISY
# ---------------------------
for _ in range(50):
    f, c = random.choice(foods)
    g = random.choice([100, 200])
    total = cal(f, g, c)

    data.append({
        "id": next_id(),
        "category": "CAL_NOISY",
        "input": f"{f.upper()}{g}Gandbanana100g",
        "expected_mode": "calorie_input",
        "must_contain": [f]
    })

# ---------------------------
# 4. FAKE FOOD
# ---------------------------
for _ in range(50):
    f = random.choice(fake_foods)
    data.append({
        "id": next_id(),
        "category": "CAL_FAKE",
        "input": f"{f} 200g",
        "expected_mode": "calorie_input",
        "must_contain_any": ["not found", "could not", "unclear"]
    })

# ---------------------------
# 5. PARTIAL UNKNOWN
# ---------------------------
for _ in range(50):
    f, c = random.choice(foods)
    fake = random.choice(fake_foods)
    g = 100
    total = cal(f, g, c)

    data.append({
        "id": next_id(),
        "category": "CAL_PARTIAL",
        "input": f"{f} 100g and {fake} 100g",
        "expected_mode": "calorie_input",
        "expected_total_calories": total,
        "must_contain": [str(total)]
    })

# ---------------------------
# 6. GUARDRAILS
# ---------------------------
guard_inputs = [
    "apple two hundred grams",
    "200g",
    "apple",
    "",
    "   ",
    "apple -200g",
    "banana g100"
]

for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "CAL_GUARD",
        "input": random.choice(guard_inputs),
        "expected_mode": "calorie_input"
    })

# ---------------------------
# 7. QNA GROUNDED
# ---------------------------
qna = [
    "What is malnutrition?",
    "What are protein sources?",
    "What are vitamin deficiencies?",
    "What is stunting?",
]

for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "QNA_GROUNDED",
        "input": random.choice(qna),
        "expected_mode": "nutrition_qa"
    })

# ---------------------------
# 8. QNA PARAPHRASE
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "QNA_PARAPHRASE",
        "input": "foods good for protein",
        "expected_mode": "nutrition_qa"
    })

# ---------------------------
# 9. QNA OOD
# ---------------------------
ood = [
    "quantum nutrition theory",
    "how to boost GPU with diet",
    "football result yesterday"
]

for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "QNA_OOD",
        "input": random.choice(ood),
        "expected_mode": "nutrition_qa"
    })

# ---------------------------
# 10. MEMORY QA
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "MEMORY_QA",
        "steps": [
            {"input": "What is protein?"},
            {"input": "What is protein again?"}
        ],
        "expected_mode": "nutrition_qa"
    })

# ---------------------------
# 11. MEAL MEMORY
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "MEAL_MEMORY",
        "steps": [
            {"input": "apple 100g"},
            {"input": "banana 100g"},
            {"input": "what is total now?"}
        ],
        "expected_mode": "calorie_input"
    })

# ---------------------------
# 12. MIXED
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "MIXED",
        "input": "apple 100g and what is protein?",
        "expected_mode": "calorie_input"
    })

# ---------------------------
# 13. DAILY TRACKING
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "DAILY_TRACKING",
        "input": "show weekly report",
        "expected_mode": "calorie_input"
    })

# ---------------------------
# 14. EXTRA STRESS
# ---------------------------
for _ in range(50):
    data.append({
        "id": next_id(),
        "category": "STRESS",
        "input": "apple100gbanana200gmango300gkiwi100g",
        "expected_mode": "calorie_input"
    })

with open("eval/datasets/eval_FINAL_ULTRA_700.json", "w") as f:
    json.dump(data, f, indent=2)

print("✅ ULTRA 700 dataset generated")
