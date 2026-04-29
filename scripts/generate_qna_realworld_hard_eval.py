import json
from pathlib import Path


OUTPUT_PATH = Path("eval/datasets/eval_cases_qna_realworld_hard.json")


TOPICS = [
    {
        "topic": "dietary_recall_period",
        "reference_answer": (
            "A person estimates intake for a specific period by recalling all foods "
            "and beverages consumed during that time. Visual aids, portion references, "
            "or measurement tools can improve accuracy."
        ),
        "expected_contains_any": [
            "recall", "foods", "beverages", "period", "visual aids", "measurement", "portion"
        ],
        "questions": [
            "I forgot exactly what I ate this week. How do nutrition studies usually estimate intake for a chosen period?",
            "When someone says they estimated their intake for a time period, what are they actually doing?",
            "How can a person reconstruct everything they ate and drank during a specific window?",
            "For diet tracking research, how is intake over a defined period usually collected?",
            "If I need to report what I consumed over a past interval, what method is normally used?",
            "How do researchers help people estimate food and drink intake for a set time span?",
            "What does dietary intake estimation over a specific period involve?",
            "How can someone remember all foods and beverages consumed during a recall period?",
            "What is the basic idea behind estimating intake for a selected time window?",
            "How are foods and drinks remembered when estimating intake for a certain period?",
            "In simple words, how does someone estimate what they consumed during a period?",
            "What should a person include when recalling intake for a defined time range?",
            "If a nutritionist asks about my intake for a period, what information should I give?",
            "How can visual aids support intake estimation for a specific period?",
            "What makes dietary recall for a time period more accurate?",
            "How is food intake usually estimated when direct measurement is not available?",
            "What is meant by recalling foods and beverages for a time interval?",
            "How can portion references help someone estimate what they ate over a period?",
            "What kind of process is used to estimate diet over a past time window?",
            "How do you explain dietary recall for a specific period to a beginner?",
            "If someone cannot remember exact portions, what can help them estimate intake?",
            "How can measuring tools improve reporting of food intake from memory?",
            "What does a dietary recall period ask a person to remember?",
            "How do people estimate both food and beverage intake from a past period?",
            "Why are visual aids useful when estimating what someone consumed?",
        ],
    },
    {
        "topic": "previous_day_recall",
        "reference_answer": (
            "People remember dietary habits over the past day by recalling meals, snacks, "
            "and drinks from the previous day. Visual aids and measuring tools can help "
            "with portion estimation."
        ),
        "expected_contains_any": [
            "previous day", "past day", "meals", "snacks", "drinks", "recall", "portion"
        ],
        "questions": [
            "How would I explain what I ate yesterday in a nutrition interview?",
            "What does someone usually report in a previous-day food recall?",
            "If a dietitian asks about the last day, what should the person remember?",
            "How do people reconstruct yesterday's meals, snacks, and drinks?",
            "What is the usual approach for remembering food intake from the past day?",
            "How can someone recall drinks and snacks from yesterday more accurately?",
            "What does a 1-day diet recall normally include?",
            "How are yesterday's eating habits usually collected in nutrition studies?",
            "If I am asked about my diet over the past 24 hours, what should I list?",
            "What should be included when reporting the previous day's intake?",
            "How can visual aids help someone remember what they ate yesterday?",
            "What tools can make yesterday's food recall more accurate?",
            "How does a person remember meals from the day before?",
            "What does past-day dietary recall mean?",
            "How can someone estimate portions from yesterday's meals?",
            "When recalling yesterday's diet, why are snacks and beverages important?",
            "What information is needed in a previous-day nutrition recall?",
            "How can someone report yesterday's breakfast, lunch, dinner, and snacks?",
            "What is the process for remembering the last 24 hours of eating?",
            "How can portion guides help with remembering yesterday's intake?",
            "What are common steps in recalling food from the previous day?",
            "How should a person describe food and drink consumed yesterday?",
            "What makes a past-day recall more reliable?",
            "How can measuring tools support a 24-hour food recall?",
            "Why is it useful to think through meals and snacks from yesterday?",
        ],
    },
    {
        "topic": "recall_tools",
        "reference_answer": (
            "Tools that help dietary recall include food pictures, portion-size references, "
            "measuring cups, scales, and other visual aids. These tools support more accurate "
            "portion and intake estimation."
        ),
        "expected_contains_any": [
            "pictures", "portion", "measuring", "cups", "scales", "visual aids", "accuracy"
        ],
        "questions": [
            "What can help someone estimate portion sizes from memory?",
            "Which tools are useful if a person cannot remember how much they ate?",
            "How do pictures of foods help during dietary recall?",
            "What aids make recent food intake recall more accurate?",
            "Can measuring cups help with remembering food portions?",
            "What should researchers use to help people estimate serving sizes?",
            "Which visual tools support better dietary recall?",
            "How can portion-size references improve food intake reports?",
            "What practical tools help someone recall meals more accurately?",
            "Why would a scale or measuring cup be useful in nutrition recall?",
            "What can a dietitian show someone to help estimate portions?",
            "How can visual examples improve reporting of recent intake?",
            "What resources are helpful for remembering food quantities?",
            "Which aids are used to estimate food intake when memory is uncertain?",
            "How can food photos support a dietary recall interview?",
            "What tools improve accuracy when recalling snacks and meals?",
            "What helps people avoid guessing portion sizes too randomly?",
            "How can someone estimate servings without exact measurements?",
            "What type of aids help with portion-size estimation?",
            "Why are visual aids important in dietary assessment?",
            "What can make a food recall less dependent on pure memory?",
            "How do portion guides help in nutrition studies?",
            "Which objects can help estimate how much food was eaten?",
            "What could someone use to remember recent food intake better?",
            "How can measurement tools improve dietary recall accuracy?",
        ],
    },
    {
        "topic": "recall_limitation",
        "reference_answer": (
            "A limitation of 24-hour recall is that one day may not represent usual intake. "
            "The method also depends on memory and accurate self-reporting, so errors can occur."
        ),
        "expected_contains_any": [
            "limitation", "24-hour", "one day", "usual intake", "memory", "self-reporting", "error"
        ],
        "questions": [
            "Why is one day of food data not always enough?",
            "What is a problem with relying only on yesterday's diet?",
            "Why might a 24-hour recall fail to show someone's normal eating pattern?",
            "What weakness does the 24-hour recall method have in nutrition research?",
            "How can memory affect a previous-day diet recall?",
            "Why can self-reported food intake be inaccurate?",
            "What is one limitation of asking people what they ate in the last 24 hours?",
            "Why does a single day not always represent usual intake?",
            "What can go wrong when people report yesterday's food from memory?",
            "Why should researchers be careful with 24-hour recall results?",
            "What makes 24-hour dietary recall imperfect?",
            "Why might someone underreport or forget foods in a 24-hour recall?",
            "What is the risk of using only one recall day?",
            "Why can a previous-day recall contain errors?",
            "How does forgetfulness affect dietary assessment?",
            "Why might yesterday's intake be different from normal intake?",
            "What is a weakness of using just one day to assess diet?",
            "Why can the 24-hour recall method be unreliable sometimes?",
            "What limitation comes from depending on memory in diet recall?",
            "Why is usual intake hard to infer from one 24-hour recall?",
            "What problem happens if the recalled day was unusual?",
            "Why is dietary recall not always perfectly accurate?",
            "What should be considered when interpreting a single 24-hour recall?",
            "Why may one-day recall need repeated measurements?",
            "What is the main concern with 24-hour recall data quality?",
        ],
    },
]


def main() -> None:
    cases = []

    for topic in TOPICS:
        for question in topic["questions"]:
            cases.append(
                {
                    "id": f"QNA_HARD_{len(cases) + 1:03d}",
                    "category": "QNA_REALWORLD_HARD",
                    "topic": topic["topic"],
                    "input": question,
                    "expected_intent": "nutrition_qa",
                    "expected_contains_any": topic["expected_contains_any"],
                    "should_not_contain": [
                        "calories per 100g",
                        "matched food",
                        "meal memory",
                        "I could not find",
                        "Please include the food name",
                        "Please provide the food quantity",
                    ],
                    "min_similarity_to_reference": 0.85,
                    "reference_answer": topic["reference_answer"],
                }
            )

    assert len(cases) == 100, len(cases)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(cases, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Written {len(cases)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
