import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

RANDOMIZED_DATASET_PATH = os.path.join(
    ROOT_DIR,
    "eval",
    "datasets",
    "eval_cases_randomized.json",
)


def main():
    if not os.path.exists(RANDOMIZED_DATASET_PATH):
        raise FileNotFoundError(
            f"Randomized dataset not found at: {RANDOMIZED_DATASET_PATH}\n"
            f"Run: PYTHONPATH=. python scripts/generate_randomized_eval_dataset.py"
        )

    os.environ["EVAL_DATASET_PATH"] = RANDOMIZED_DATASET_PATH

    from scripts.run_eval import main as run_eval_main

    print("=" * 70)
    print("Running RANDOMIZED evaluation")
    print("=" * 70)
    print(f"Using dataset: {RANDOMIZED_DATASET_PATH}")
    print("=" * 70)

    run_eval_main()


if __name__ == "__main__":
    main()