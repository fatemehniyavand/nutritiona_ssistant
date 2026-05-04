import json
from pathlib import Path

report = json.loads(Path("eval/outputs/eval_report.json").read_text())

fails = report["failed_cases"][:10]

print("\n===== FAILURE ANALYSIS =====\n")

for f in fails:
    print("ID:", f["id"])
    print("Input:", f["input"])
    print("Answer:", f["answer"])
    print("Score:", f["score"])
    print("Behavior:", f.get("behavior_score"))
    print("Content:", f.get("content_score"))
    print("Failures:", f["failures"])
    print("-" * 60)
