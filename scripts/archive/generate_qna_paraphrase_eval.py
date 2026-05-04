import json
from pathlib import Path


OUTPUT_PATH = Path("eval/datasets/eval_cases_qna_paraphrase.json")


BASE_CASES = [
    {
        "topic": "dietary_recall_period",
        "reference_answer": (
            "During this process, a person recalls all foods and beverages consumed "
            "within a specific period. Measurement tools, portion references, or visual aids "
            "can help improve estimation accuracy."
        ),
        "questions": [
            "How can someone estimate what they ate during a certain time window?",
            "What is the method for working out food intake over a specific period?",
            "How do researchers ask people to estimate their intake for a past period?",
            "What does it mean to estimate dietary intake for a defined time span?",
            "How is food and drink intake usually estimated for a chosen period?",
            "What steps help someone report what they consumed during a time period?",
            "How can a person reconstruct their eating and drinking over a past interval?",
            "What is involved in estimating intake during a specific dietary recall period?",
            "How can someone describe all food and beverages consumed in a given period?",
            "What process is used to remember intake from a particular time window?"
        ],
        "expected_contains_any": [
            "recall", "foods", "beverages", "period", "visual aids", "measurement"
        ],
    },
    {
        "topic": "previous_day_recall",
        "reference_answer": (
            "People usually recall meals, snacks, and drinks from the previous day. "
            "Visual aids, portion-size guides, or measuring tools may help them remember "
            "more accurately."
        ),
        "questions": [
            "What do people usually do to remember what they ate yesterday?",
            "How can someone report their meals from the previous day?",
            "What helps a person remember yesterday's food and drinks?",
            "How do people recall their eating habits over the last day?",
            "What is the usual way to describe food intake from the past 24 hours?",
            "How can someone reconstruct yesterday's meals and snacks?",
            "What should a person think about when recalling yesterday's diet?",
            "How are meals and drinks from the previous day usually remembered?",
            "What does a person report in a one-day dietary recall?",
            "How can someone remember snacks and drinks from the day before?"
        ],
        "expected_contains_any": [
            "previous day", "meals", "snacks", "drinks", "recall", "visual aids"
        ],
    },
    {
        "topic": "recall_tools",
        "reference_answer": (
            "Helpful aids include pictures of foods, portion-size references, measuring cups, "
            "scales, or other visual tools that support more accurate dietary recall."
        ),
        "questions": [
            "Which aids can improve accuracy when recalling recent food intake?",
            "What tools may help someone remember what they recently ate?",
            "What can support a person during dietary recall?",
            "Which visual aids are useful for estimating recent meals?",
            "What items help people estimate portion sizes in dietary recall?",
            "How can pictures or measuring tools help with food recall?",
            "What can make recent food intake recall more accurate?",
            "Which tools are useful when estimating portions from memory?",
            "What kind of aids help people remember their recent diet?",
            "What resources can improve recall of meals and portion sizes?"
        ],
        "expected_contains_any": [
            "pictures", "portion size", "measuring", "visual aids", "food items"
        ],
    },
    {
        "topic": "recall_limitation",
        "reference_answer": (
            "A limitation of the 24-hour recall method is that one day may not represent "
            "a person's usual intake, and the result depends on memory and accurate reporting."
        ),
        "questions": [
            "What is a weakness of asking someone about only the last 24 hours of eating?",
            "Why can a 24-hour dietary recall be limited?",
            "What is one problem with using only yesterday's intake in nutrition studies?",
            "Why might one day of food recall not be enough?",
            "What makes the 24-hour recall method imperfect?",
            "What is a limitation of collecting diet data from just one day?",
            "Why may a single 24-hour recall not show usual eating habits?",
            "What issue can occur when people report only the previous day's food?",
            "Why is memory a problem in 24-hour dietary recall?",
            "What weakness does the 24-hour recall method have?"
        ],
        "expected_contains_any": [
            "limitation", "24-hour recall", "not represent", "usual intake", "memory"
        ],
    },
]


def main() -> None:
    cases = []

    for base in BASE_CASES:
        for question in base["questions"]:
            cases.append(
                {
                    "id": f"QNA_SIM_{len(cases) + 1:03d}",
                    "category": "QNA_PARAPHRASE",
                    "topic": base["topic"],
                    "input": question,
                    "expected_intent": "nutrition_qa",
                    "expected_contains_any": base["expected_contains_any"],
                    "should_not_contain": [
                        "calories per 100g",
                        "matched food",
                        "meal memory",
                        "I could not find"
                    ],
                    "min_similarity_to_reference": 0.75,
                    "reference_answer": base["reference_answer"],
                }
            )

    assert len(cases) == 40, len(cases)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(cases, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Written {len(cases)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
