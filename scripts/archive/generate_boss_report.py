import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_JSON = Path("eval/outputs/boss_eval_report.json")
REPORT_MD = Path("eval/outputs/final_boss_evaluation_report.md")
CHART_PATH = Path("eval/outputs/boss_category_pass_rate.png")

report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

categories = report["category_breakdown"]
labels = list(categories.keys())
rates = [
    round((v["passed"] / v["total"]) * 100, 2) if v["total"] else 0
    for v in categories.values()
]

plt.figure(figsize=(12, 6))
plt.bar(labels, rates)
plt.xticks(rotation=45, ha="right")
plt.ylabel("Pass Rate (%)")
plt.title("Final Boss Evaluation - Category Pass Rate")
plt.tight_layout()
plt.savefig(CHART_PATH)

lines = []
lines.append("# Nutrition Assistant - Final Boss Evaluation Report")
lines.append("")
lines.append("## Overall Result")
lines.append("")
lines.append(f"- Dataset: `{report['dataset']}`")
lines.append(f"- Total cases: **{report['total']}**")
lines.append(f"- Passed: **{report['passed']}**")
lines.append(f"- Failed: **{report['failed']}**")
lines.append(f"- Pass rate: **{report['pass_rate']}%**")
lines.append("")
lines.append("## Category Breakdown")
lines.append("")
lines.append("| Category | Total | Passed | Failed | Pass Rate |")
lines.append("|---|---:|---:|---:|---:|")

for cat, stats in categories.items():
    total = stats["total"]
    passed = stats["passed"]
    failed = stats["failed"]
    rate = round((passed / total) * 100, 2) if total else 0
    lines.append(f"| {cat} | {total} | {passed} | {failed} | {rate}% |")

lines.append("")
lines.append("## Failed Cases")
lines.append("")

failed_cases = [r for r in report["results"] if not r["passed"]]
if not failed_cases:
    lines.append("No failed cases.")
else:
    for r in failed_cases:
        lines.append(f"### {r['id']} - {r['category']}")
        for e in r["errors"]:
            lines.append(f"- {e}")
        lines.append("")

lines.append("")
lines.append("## Chart")
lines.append("")
lines.append(f"![Category pass rate]({CHART_PATH.name})")
lines.append("")
lines.append("## What This Evaluation Tests")
lines.append("")
lines.append("- Exact calorie calculation")
lines.append("- Decimal grams and rounding")
lines.append("- Multi-item calorie totals")
lines.append("- Noisy and glued input parsing")
lines.append("- Fresh vs canned food distinction")
lines.append("- Fake food rejection and hallucination prevention")
lines.append("- Partial unknown food handling")
lines.append("- Guardrails for invalid quantities and unsafe inputs")
lines.append("- Grounded nutrition Q&A retrieval")
lines.append("- Q&A paraphrase robustness")
lines.append("- Medical-safety and out-of-domain rejection")
lines.append("- Same/similar question memory")
lines.append("- Meal memory: add, total, remove, clear")
lines.append("- Mixed calorie + Q&A request handling")
lines.append("- Daily and weekly calorie tracking")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {REPORT_MD}")
print(f"Wrote {CHART_PATH}")
