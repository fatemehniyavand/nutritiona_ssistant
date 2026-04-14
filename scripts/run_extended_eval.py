import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

EXTENDED_DATASET_PATH = os.path.join(
    ROOT_DIR,
    "eval",
    "datasets",
    "eval_cases_extended.json",
)


def main():
    if not os.path.exists(EXTENDED_DATASET_PATH):
        raise FileNotFoundError(
            f"Extended dataset not found at: {EXTENDED_DATASET_PATH}\n"
            f"Run: PYTHONPATH=. python scripts/generate_extended_eval_dataset.py"
        )

    os.environ["EVAL_DATASET_PATH"] = EXTENDED_DATASET_PATH

    from scripts.run_eval import main as run_eval_main

    print("=" * 70)
    print("Running EXTENDED evaluation")
    print("=" * 70)
    print(f"Using dataset: {EXTENDED_DATASET_PATH}")
    print("=" * 70)

    run_eval_main()


if __name__ == "__main__":
    main()