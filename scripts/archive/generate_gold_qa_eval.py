import json
from pathlib import Path

out = Path("eval/datasets/eval_cases_qna_gold.json")

topics = [
    (
        "24_hour_recall_limitation",
        "One limitation of 24-hour dietary recall is that a single day may not represent usual intake, and accuracy depends on memory and honest reporting.",
        [
            "What is one limitation of 24-hour dietary recall?",
            "Why can a 24-hour food recall be inaccurate?",
            "Why might one day of diet data not represent normal eating?",
            "What is a weakness of asking people what they ate yesterday?",
            "How does memory affect 24-hour dietary recall?",
        ],
    ),
    (
        "dietary_recall_tools",
        "Dietary recall can be improved using food images, portion-size guides, measuring cups, food scales, and other visual aids.",
        [
            "What tools help improve dietary recall accuracy?",
            "How can people estimate portions more accurately during recall?",
            "Which aids help someone remember what they ate?",
            "Why are food pictures useful in dietary recall?",
            "How can measuring cups or scales support dietary assessment?",
        ],
    ),
    (
        "balanced_diet",
        "A balanced diet provides essential nutrients, supports health, helps prevent deficiencies, and should include variety across food groups.",
        [
            "Why is a balanced diet important?",
            "What does a balanced diet provide?",
            "How does dietary variety support health?",
            "Why should people eat different food groups?",
            "How can a balanced diet help prevent deficiencies?",
        ],
    ),
    (
        "extreme_diets",
        "Extreme diets can be harmful because they may cause nutrient deficiencies, low energy, unhealthy weight changes, and other health risks.",
        [
            "Can extreme diets be harmful?",
            "Why are very restrictive diets risky?",
            "What problems can happen from cutting out many foods?",
            "Why should people avoid extreme dieting?",
            "How can restrictive diets affect health?",
        ],
    ),
    (
        "carbohydrates",
        "Carbohydrates are not automatically bad. They are an important energy source, and quality, portion size, and overall diet matter.",
        [
            "Are carbohydrates always bad?",
            "Why do people need carbohydrates?",
            "Are all carbs unhealthy?",
            "How should someone think about carbs in a diet?",
            "Do carbs always cause weight gain?",
        ],
    ),
    (
        "fruit_sugar",
        "Fruit contains natural sugar, but it also provides fiber, vitamins, minerals, and water. Whole fruit can be part of a balanced diet.",
        [
            "Is fruit bad because it has sugar?",
            "Should people avoid fruit sugar completely?",
            "Why is whole fruit different from sugary drinks?",
            "Can fruit be part of a healthy diet?",
            "What nutrients does fruit provide besides sugar?",
        ],
    ),
    (
        "protein",
        "Protein supports tissue repair, muscle maintenance, enzymes, hormones, and immune function, but needs vary by age, activity, and health status.",
        [
            "Why is protein important?",
            "What does protein do in the body?",
            "Does everyone need the same amount of protein?",
            "How does protein support muscles?",
            "Why is protein needed for health?",
        ],
    ),
    (
        "fiber",
        "Fiber supports digestion, bowel regularity, fullness, and can help support heart and metabolic health when part of a balanced diet.",
        [
            "Why is fiber important?",
            "How does fiber help digestion?",
            "Can fiber help people feel full?",
            "What are benefits of dietary fiber?",
            "Why should someone eat fiber-rich foods?",
        ],
    ),
    (
        "hydration",
        "Water is essential for body functions including temperature regulation, digestion, circulation, and waste removal.",
        [
            "Why is water important for the body?",
            "What does hydration help with?",
            "Why do humans need water?",
            "How does water support normal body function?",
            "What are the roles of water in health?",
        ],
    ),
    (
        "processed_foods",
        "Processed foods are not all the same. Some can fit in a diet, but highly processed foods high in added sugar, salt, or unhealthy fats should be limited.",
        [
            "Are all processed foods bad?",
            "Should processed foods always be avoided?",
            "How should people think about processed foods?",
            "Why are some highly processed foods less healthy?",
            "Can processed foods fit into a balanced diet?",
        ],
    ),
]

cases = []
for topic, reference, questions in topics:
    for q in questions:
        cases.append({
            "id": f"GOLD_{len(cases) + 1:03d}",
            "category": "QNA_GOLD",
            "case_type": "gold_content",
            "topic": topic,
            "input": q,
            "expected_intent": "nutrition_qa",
            "reference_answer": reference,
            "min_similarity_to_reference": 0.35,
            "expected_contains_any": reference.lower().replace(".", "").split()[:8],
            "should_not_contain": [
                "I could not find",
                "matched food",
                "meal memory",
                "estimated calories",
                "outside nutrition"
            ]
        })

assert len(cases) == 50, len(cases)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Written {len(cases)} gold QA cases to {out}")
