import sys
import shutil
import subprocess
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: PYTHONPATH=. python eval/evaluate_any.py <dataset_path>")
    sys.exit(1)

dataset = Path(sys.argv[1])
main = Path("eval/datasets/eval_cases.json")
backup = Path("eval/datasets/eval_cases.backup.tmp.json")

if not dataset.exists():
    print(f"Dataset not found: {dataset}")
    sys.exit(1)

shutil.copy(main, backup)
shutil.copy(dataset, main)

try:
    subprocess.run(["python", "eval/evaluate.py"], check=True)
finally:
    shutil.copy(backup, main)
    backup.unlink(missing_ok=True)
