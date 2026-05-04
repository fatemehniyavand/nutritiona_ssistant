import json
from pathlib import Path


DATASET_PATH = Path("eval/datasets/eval_cases.json")
BACKUP_PATH = Path("eval/datasets/eval_cases.before_input_fix.json")


def build_input_from_meta_items(items):
    parts = []
    for idx, item in enumerate(items):
        food, grams = item[0], item[1]
        part = f"{food} {grams}g"
        if idx == 0:
            parts.append(part)
        else:
            parts.append(f"and {part}")
    return " ".join(parts)


def main():
    cases = json.loads(DATASET_PATH.read_text())

    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(cases, indent=2, ensure_ascii=False))

    fixed = 0

    for case in cases:
        meta_items = case.get("meta", {}).get("items")

        if not meta_items:
            continue

        expected_total_items = case.get("expected", {}).get("total_items")

        if expected_total_items != len(meta_items):
            continue

        old_input = case.get("input", "")
        new_input = build_input_from_meta_items(meta_items)

        if old_input != new_input:
            case["input"] = new_input
            case.setdefault("meta", {})["original_input_before_fix"] = old_input
            fixed += 1

    DATASET_PATH.write_text(json.dumps(cases, indent=2, ensure_ascii=False))

    print(f"Fixed {fixed} dataset input(s).")
    print(f"Backup saved at: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
