import json
from pathlib import Path
import matplotlib.pyplot as plt

behavior = json.loads(Path("eval/outputs/reports/behavior_report.json").read_text())
gold = json.loads(Path("eval/outputs/reports/gold_report.json").read_text())

labels = ["Behavior", "Gold QA"]
values = [behavior["pass_rate"], gold["pass_rate"]]

plt.figure(figsize=(7, 4))
plt.bar(labels, values)
plt.ylim(0, 110)
plt.ylabel("Pass Rate (%)")
plt.title("Nutrition Assistant Evaluation Results")

for i, v in enumerate(values):
    plt.text(i, v + 2, f"{v:.1f}%", ha="center")

Path("eval/outputs").mkdir(parents=True, exist_ok=True)
plt.tight_layout()
plt.savefig("eval/outputs/eval_plot.png")

print("Saved: eval/outputs/eval_plot.png")
