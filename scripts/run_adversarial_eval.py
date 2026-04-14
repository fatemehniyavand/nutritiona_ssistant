import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

ADVERSARIAL_DATASET_PATH = os.path.join(
    ROOT_DIR,
    "eval",
    "datasets",
    "eval_cases_adversarial.json",
)


def main():
    if not os.path.exists(ADVERSARIAL_DATASET_PATH):
        raise FileNotFoundError(
            f"Adversarial dataset not found at: {ADVERSARIAL_DATASET_PATH}\n"
            f"Run: PYTHONPATH=. python scripts/generate_adversarial_eval_dataset.py"
        )

    os.environ["EVAL_DATASET_PATH"] = ADVERSARIAL_DATASET_PATH

    from scripts.run_eval import main as run_eval_main

    print("=" * 70)
    print("Running ADVERSARIAL evaluation")
    print("=" * 70)
    print(f"Using dataset: {ADVERSARIAL_DATASET_PATH}")
    print("=" * 70)

    run_eval_main()


if __name__ == "__main__":
    main()