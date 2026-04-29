import json
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt


OUT_DIR = Path("docs/reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BEHAVIOR_PATH = Path("eval/outputs/reports/behavior_report.json")
GOLD_PATH = Path("eval/outputs/reports/gold_report.json")

behavior = json.loads(BEHAVIOR_PATH.read_text(encoding="utf-8"))
gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def save_case_type_chart(report, output_path):
    breakdown = report.get("case_type_breakdown", {})
    labels = list(breakdown.keys())
    rates = [
        breakdown[k]["passed"] / breakdown[k]["total"] * 100
        for k in labels
    ]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, rates)
    plt.ylim(0, 100)
    plt.ylabel("Pass Rate (%)")
    plt.xlabel("Case Type")
    plt.title("Behavior Evaluation Pass Rate by Case Type")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


chart_path = OUT_DIR / "behavior_case_type_pass_rate.png"
save_case_type_chart(behavior, chart_path)


md = f"""# Nutrition Assistant Evaluation Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 1. Executive Summary

This project evaluates a Nutrition Assistant with two complementary evaluation strategies:

1. **Behavior-based evaluation** checks safety, routing, and robustness.
2. **Gold QA evaluation** checks semantic correctness against reference answers.

The system includes a **pre-RAG QA Safety Router** that catches risky or irrelevant inputs before retrieval. This prevents raw RAG hallucinations and improves reliability.

---

## 2. Behavior-Based Evaluation

Dataset: `eval_cases_qna_behavior.json`

| Metric | Value |
|---|---:|
| Total cases | {behavior["total_cases"]} |
| Passed cases | {behavior["passed_cases"]} |
| Failed cases | {len(behavior["failed_cases"])} |
| Pass rate | {behavior["pass_rate"]}% |

### Case Type Breakdown

| Case Type | Total | Passed | Failed | Pass Rate |
|---|---:|---:|---:|---:|
"""

for case_type, stats in behavior["case_type_breakdown"].items():
    rate = stats["passed"] / stats["total"] * 100
    md += f"| {case_type} | {stats['total']} | {stats['passed']} | {stats['failed']} | {rate:.2f}% |\n"

md += f"""

![Behavior pass rate by case type](behavior_case_type_pass_rate.png)

---

## 3. Gold QA Evaluation

Dataset: `eval_cases_qna_gold.json`

| Metric | Value |
|---|---:|
| Total cases | {gold["total_cases"]} |
| Passed cases | {gold["passed_cases"]} |
| Failed cases | {len(gold["failed_cases"])} |
| Pass rate | {gold["pass_rate"]}% |

The Gold QA dataset focuses on content correctness. It uses reference answers and similarity-based content scoring.

---

## 4. Dual Scoring

The evaluator reports two complementary dimensions:

| Score Type | Purpose |
|---|---|
| Behavior Score | Measures safety behavior, routing quality, refusal behavior, clarification, and avoidance of unsafe claims |
| Content Score | Measures answer similarity to reference answers |

This separation is important because a safe response and a semantically complete response are not the same thing.

---

## 5. Before vs After Safety Router

Before adding the QA Safety Router, strict behavior evaluation exposed failures such as:

- out-of-domain questions being sent to RAG
- misinformation questions receiving raw retrieved answers
- ambiguous questions not asking for clarification
- mixed calorie + QA inputs causing mode confusion
- typo/noisy queries being mishandled

After adding the pre-RAG QA Safety Router, the behavior evaluation reached **{behavior["pass_rate"]}%**.

---

## 6. Failure Analysis

Latest behavior run:

- Failed cases: **{len(behavior["failed_cases"])}**

"""

if behavior["failed_cases"]:
    md += "### Failed Case Examples\n\n"
    for f in behavior["failed_cases"][:10]:
        md += f"""#### {f["id"]} - {f.get("case_type")}

**Input:** {f["input"]}

**Answer:** {f["answer"]}

**Failures:** {f["failures"]}

---
"""
else:
    md += "No failed cases were found in the latest behavior evaluation run.\n"

md += """

---

## 7. Conclusion

The system now demonstrates:

- robust pre-RAG safety routing
- behavior-based QA validation
- content-based Gold QA validation
- explainable evaluation reports
- clear case-type breakdowns

This makes the project significantly stronger than a simple RAG chatbot because it evaluates not only whether the assistant answers, but whether it behaves safely and correctly across difficult inputs.
"""

report_path = OUT_DIR / "evaluation_report.md"
report_path.write_text(md, encoding="utf-8")

print(f"Markdown report written to: {report_path}")
print(f"Chart written to: {chart_path}")
