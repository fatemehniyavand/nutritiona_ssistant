import json
from pathlib import Path

OUT = Path("eval/datasets")
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# FINAL CALORIE MODE DATASET
# ============================================================

foods = {
    "applesauce": 62,
    "canned apricots": 48,
    "canned blackberries": 92,
    "canned blueberries": 88,
    "canned cherries": 54,
    "canned cranberries": 178,
    "canned crushed pineapple": 53,
    "canned figs": 107,
    "canned fruit cocktail": 81,
    "canned fruit salad": 50,
    "canned grapefruit": 37,
    "canned grapes": 76,
    "canned mandarin oranges": 71,
    "canned mango": 65,
    "canned pineapple": 60,
    "canned peaches": 54,
    "canned pears": 35,
    "canned raspberries": 91,
    "canned sliced pineapple": 53,
    "apple": 52,
    "avocado": 160,
    "banana": 89,
    "blueberries": 57,
    "mango": 60,
    "pineapple": 50,
    "potato": 77,
    "baked potato": 93,
    "boiled potatoes": 87,
    "french fries": 312,
    "mashed potatoes": 89,
    "gnocchi": 133,
    "potato salad": 143,
    "potato wedges": 123,
}

grams_list = [50, 75, 100, 120, 150, 200, 250, 300]

cal_cases = []
case_id = 1

def kcal(food, grams):
    return round((foods[food] * grams) / 100, 2)

def add_cal_case(category, kind, inp, expected, meta=None):
    global case_id
    cal_cases.append({
        "case_id": f"CAL_FINAL_{case_id:03d}",
        "category": category,
        "kind": kind,
        "input": inp,
        "expected": expected,
        "meta": meta or {}
    })
    case_id += 1

# Single clean inputs
for food in list(foods.keys())[:30]:
    for grams in [50, 100, 200]:
        add_cal_case(
            "CAL_EXACT",
            "single_turn",
            f"{food} {grams}g",
            {
                "mode": "calorie",
                "total_calories": kcal(food, grams),
                "matched_items": 1,
                "total_items": 1,
                "coverage": 1.0
            },
            {"food": food, "grams": grams}
        )

# No-space / normalization cases
for food in ["apple", "banana", "avocado", "canned pineapple", "french fries", "mashed potatoes"]:
    compact = food.replace(" ", "")
    for grams in [100, 200]:
        add_cal_case(
            "CAL_NORMALIZATION",
            "single_turn",
            f"{compact}{grams}g",
            {
                "mode": "calorie",
                "total_calories": kcal(food, grams),
                "matched_items": 1,
                "total_items": 1,
                "coverage": 1.0
            },
            {"food": food, "grams": grams, "normalization": True}
        )

# Multi-item cases
multi_items = [
    [("apple", 200), ("banana", 100)],
    [("canned pineapple", 100), ("mango", 200)],
    [("french fries", 150), ("potato salad", 100)],
    [("avocado", 120), ("blueberries", 75)],
    [("baked potato", 200), ("canned peaches", 100)],
    [("mashed potatoes", 150), ("gnocchi", 200)],
]

for items in multi_items:
    text = " and ".join([f"{f} {g}g" for f, g in items])
    total = round(sum(kcal(f, g) for f, g in items), 2)
    add_cal_case(
        "CAL_MULTI",
        "single_turn",
        text,
        {
            "mode": "calorie",
            "total_calories": total,
            "matched_items": len(items),
            "total_items": len(items),
            "coverage": 1.0
        },
        {"items": items}
    )

# Multi-turn memory cases
memory_sequences = [
    [("apple 200g", "banana 100g", "what is the total now?"), 193.0],
    [("avocado 100g", "canned pineapple 200g", "what is the total now?"), 280.0],
    [("french fries 100g", "potato wedges 100g", "what is the total now?"), 435.0],
    [("mashed potatoes 200g", "canned peaches 100g", "what is the total now?"), 232.0],
]

for steps, total in memory_sequences:
    cal_cases.append({
        "case_id": f"CAL_FINAL_{case_id:03d}",
        "category": "CAL_MEMORY",
        "kind": "multi_turn",
        "steps": list(steps),
        "expected": {
            "mode": "calorie",
            "meal_total": total,
            "matched_items": len(steps) - 1,
            "coverage": 1.0
        },
        "meta": {"memory_test": True}
    })
    case_id += 1

# Guardrail / invalid cases
guard_cases = [
    ("", "empty"),
    ("200g", "quantity_only"),
    ("apple", "food_only"),
    ("apple two hundred grams", "non_numeric_quantity"),
    ("سیب ۲۰۰ گرم", "non_english"),
    ("asd qwe zzz", "gibberish"),
    ("dragon meat 100g", "unknown_food"),
    ("cloud soup 200g", "unknown_food"),
]

for inp, reason in guard_cases:
    add_cal_case(
        "CAL_GUARDRAIL",
        "single_turn",
        inp,
        {
            "mode": "guardrail",
            "should_reject": True
        },
        {"reason": reason}
    )

Path("eval/datasets/eval_final_calorie_mode.json").write_text(
    json.dumps(cal_cases, indent=2, ensure_ascii=False)
)

# ============================================================
# FINAL QNA MODE DATASET
# ============================================================

qna_cases = []
qid = 1

def add_qna(category, inp, keywords, forbidden=None):
    global qid
    qna_cases.append({
        "case_id": f"QNA_FINAL_{qid:03d}",
        "category": category,
        "kind": "single_turn",
        "input": inp,
        "expected": {
            "mode": "qa",
            "required_keywords": keywords,
            "forbidden_phrases": forbidden or [
                "i could not find",
                "not enough information",
                "not grounded",
                "i don't know"
            ]
        },
        "meta": {}
    })
    qid += 1

# Malnutrition symptoms - paraphrased, not exact copies
malnutrition_keywords = ["underweight", "overweight", "short stature", "reduced activity", "wasting"]
for q in [
    "Which body signs can suggest that someone may be malnourished?",
    "How might malnutrition show up physically in a person?",
    "What physical clues can indicate poor nutritional status?",
    "What visible body changes may be associated with malnutrition?",
    "Which general physical symptoms are linked with malnutrition?"
]:
    add_qna("QNA_MALNUTRITION_GENERAL", q, malnutrition_keywords)

# Eye / ocular signs
eye_keywords = ["pale", "bitot", "redness", "dryness", "cornea"]
for q in [
    "What eye-related signs may suggest nutrient deficiency?",
    "Which ocular symptoms can be associated with malnutrition?",
    "How can the eyes show possible nutritional deficiency?",
    "What visual signs in the eyes may point to malnutrition?",
    "What changes around the eyes can indicate poor nutrition?"
]:
    add_qna("QNA_MALNUTRITION_EYES", q, eye_keywords)

# Clinical assessment limitation
clinical_keywords = ["early", "physical symptoms", "biochemical changes"]
for q in [
    "Why may clinical assessment fail to detect early nutrient deficiency?",
    "What is a weakness of clinical examination in early malnutrition detection?",
    "Why is clinical assessment limited for identifying initial nutrition problems?",
    "What problem occurs when relying only on physical signs for nutrient deficiency?",
    "Why can early deficiency be missed during clinical assessment?"
]:
    add_qna("QNA_CLINICAL_LIMITATION", q, clinical_keywords)

# Biochemical assessment
bio_keywords = ["blood", "urine", "body fluids", "nutritional status"]
for q in [
    "What does biochemical nutrition assessment measure?",
    "How are blood and urine used in nutritional evaluation?",
    "How can biochemical methods help assess nutrition?",
    "What is checked during biochemical assessment of nutrition?",
    "How do lab-based measures reflect nutritional status?"
]:
    add_qna("QNA_BIOCHEMICAL_ASSESSMENT", q, bio_keywords)

# Biochemical benefits
bio_benefit_keywords = ["early detection", "metabolism", "precision", "accuracy"]
for q in [
    "Why is biochemical assessment useful in nutrition evaluation?",
    "What advantages do biochemical methods have for detecting nutrition problems?",
    "How can biochemical assessment identify nutritional issues early?",
    "Why are biochemical tests considered accurate for nutrition assessment?",
    "What makes biochemical assessment reliable for detecting subtle nutritional changes?"
]:
    add_qna("QNA_BIOCHEMICAL_BENEFITS", q, bio_benefit_keywords)

# Biochemical drawbacks
bio_limit_keywords = ["time-consuming", "costly", "skilled professionals", "resources"]
for q in [
    "What are disadvantages of biochemical nutrition assessment?",
    "Why can biochemical assessment be difficult to use?",
    "What resources are needed for biochemical assessment?",
    "What makes biochemical methods expensive or difficult?",
    "Which limitations are associated with biochemical assessment?"
]:
    add_qna("QNA_BIOCHEMICAL_LIMITATIONS", q, bio_limit_keywords)

# Dietary habits importance
diet_keywords = ["food intake", "nutrients", "health", "recommendations"]
for q in [
    "Why is dietary intake important in nutrition assessment?",
    "How does someone's diet help evaluate their health?",
    "Why should eating habits be considered when assessing nutrition?",
    "How can food intake reveal nutritional problems?",
    "Why is understanding a person's usual diet useful?"
]:
    add_qna("QNA_DIETARY_HABITS", q, diet_keywords)

# 24-hour recall
recall_keywords = ["past 24 hours", "food", "beverage", "portion", "measuring"]
for q in [
    "What happens during a 24-hour dietary recall?",
    "How does a 24-hour food recall work?",
    "What does a person report in a 24-hour dietary recall?",
    "How is recent food and drink intake collected in a 24-hour recall?",
    "What tools can support portion estimation during dietary recall?"
]:
    add_qna("QNA_24H_RECALL", q, recall_keywords)

# 24-hour recall limitations
recall_limit_keywords = ["short-term memory", "typical dietary intake", "multiple recalls", "different days"]
for q in [
    "What is a limitation of the 24-hour dietary recall method?",
    "Why might one 24-hour recall not represent usual diet?",
    "How can the accuracy of 24-hour recall be improved?",
    "What problem does memory create in dietary recall?",
    "Why are repeated dietary recalls recommended?"
]:
    add_qna("QNA_24H_RECALL_LIMITATION", q, recall_limit_keywords)

# Public health nutrition
public_keywords = ["prevent disease", "prolong life", "promote wellness", "nutrition"]
for q in [
    "What is public health nutrition about?",
    "How does public health nutrition support society?",
    "What is the goal of public health nutrition?",
    "How can nutrition improve public health?",
    "What does public health nutrition aim to achieve?"
]:
    add_qna("QNA_PUBLIC_HEALTH", q, public_keywords)

# PEM
pem_keywords = ["kwashiorkor", "marasmus", "protein energy"]
for q in [
    "What are clinical forms of protein energy malnutrition?",
    "Which PEM condition is linked with edema and skin lesions?",
    "What type of PEM combines starvation and malnutrition features?",
    "What are examples of protein energy malnutrition?",
    "Which conditions are associated with PEM?"
]:
    add_qna("QNA_PEM", q, pem_keywords)

# WHO malnutrition
who_keywords = ["imbalance", "nutrients", "energy", "growth", "maintenance"]
for q in [
    "How is malnutrition defined by WHO?",
    "What does WHO mean by malnutrition?",
    "According to WHO, what causes malnutrition?",
    "How does WHO describe nutrient and energy imbalance?",
    "What is the WHO concept of malnutrition?"
]:
    add_qna("QNA_WHO_MALNUTRITION", q, who_keywords)

# OOD / forbidden QA cases
ood_questions = [
    "Who won the Champions League last year?",
    "Write Python code for a calculator.",
    "What is the capital of Japan?",
    "How do I fix my car engine?",
    "Tell me a political joke.",
    "What is the weather in Naples today?",
    "Can you diagnose my disease?",
    "Should I take antibiotics for fever?",
    "Give me a guaranteed weight loss plan in three days.",
    "What stock should I buy tomorrow?"
]

for q in ood_questions:
    qna_cases.append({
        "case_id": f"QNA_FINAL_{qid:03d}",
        "category": "QNA_OOD",
        "kind": "single_turn",
        "input": q,
        "expected": {
            "mode": "qa",
            "should_reject": True,
            "required_keywords": ["nutrition"],
            "forbidden_phrases": [
                "champions league",
                "stock",
                "weather",
                "political",
                "guaranteed"
            ]
        },
        "meta": {"ood": True}
    })
    qid += 1

Path("eval/datasets/eval_final_qna_mode.json").write_text(
    json.dumps(qna_cases, indent=2, ensure_ascii=False)
)

print("✅ Created eval/datasets/eval_final_calorie_mode.json")
print("✅ Calorie cases:", len(cal_cases))
print("✅ Created eval/datasets/eval_final_qna_mode.json")
print("✅ QNA cases:", len(qna_cases))
