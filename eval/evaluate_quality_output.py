import json
import re
from pathlib import Path

DATASET = Path("eval/datasets/eval_FINAL_QUALITY_ASSERTIONS.json")
REPORT = Path("eval/outputs/eval_report.json")

def norm(s):
    return re.sub(r"\s+", " ", str(s).lower()).strip()

def flatten(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return json.dumps(x, ensure_ascii=False, sort_keys=True)

def response_text(result):
    parts = []
    if "answer" in result:
        parts.append(flatten(result["answer"]))
    raw = result.get("raw_response", {})
    if isinstance(raw, dict):
        for k in ["final_message", "items", "total_calories", "coverage", "confidence", "suggestions", "mode"]:
            if k in raw:
                parts.append(flatten(raw[k]))
    else:
        parts.append(flatten(raw))
    return "\n".join(parts)

def has_number(text, expected):
    t = norm(text)
    nums = {
        str(expected),
        str(float(expected)),
        f"{float(expected):.0f}",
        f"{float(expected):.1f}",
    }
    return any(n.lower() in t for n in nums)

def main():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    results = report.get("all_results", [])
    by_id = {r.get("id"): r for r in results if isinstance(r, dict)}

    failures = []

    for case in cases:
        cid = case["id"]
        r = by_id.get(cid)

        if not r:
            failures.append((cid, "NO_RESULT_IN_REPORT", "case not found"))
            continue

        text = response_text(r)
        t = norm(text)

        for phrase in case.get("must_contain", []):
            if norm(phrase) not in t:
                failures.append((cid, "MISSING_TEXT", phrase))

        any_list = case.get("must_contain_any", [])
        if any_list and not any(norm(p) in t for p in any_list):
            failures.append((cid, "MISSING_ANY_TEXT", " OR ".join(any_list)))

        for phrase in case.get("must_not_contain", []):
            if norm(phrase) in t:
                failures.append((cid, "FORBIDDEN_TEXT_FOUND", phrase))

        if "expected_total_calories" in case:
            if not has_number(text, case["expected_total_calories"]):
                failures.append((cid, "EXPECTED_CALORIES_NOT_FOUND", case["expected_total_calories"]))

        if "allowed_total_calories" in case:
            if not any(has_number(text, n) for n in case["allowed_total_calories"]):
                failures.append((cid, "ALLOWED_CALORIES_NOT_FOUND", case["allowed_total_calories"]))

        for food in case.get("expected_matched_foods", []):
            if norm(food) not in t:
                failures.append((cid, "EXPECTED_FOOD_NOT_FOUND", food))

    print("=" * 70)
    print("Nutrition Assistant QUALITY ASSERTION REPORT")
    print("=" * 70)
    print(f"Total quality cases : {len(cases)}")
    print(f"Quality failures    : {len(failures)}")
    print(f"Quality pass rate   : {(len(cases)-len(failures))/len(cases)*100:.2f}%")
    print("=" * 70)

    if failures:
        print("\nFailures:")
        for cid, kind, detail in failures:
            print(f"- {cid} | {kind} | {detail}")
        raise SystemExit(1)

    print("✅ All quality assertions passed.")

if __name__ == "__main__":
    main()
