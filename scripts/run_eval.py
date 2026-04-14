import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
from src.domain.models.meal_state import MealState


DATASET_PATH = os.environ.get(
    "EVAL_DATASET_PATH",
    os.path.join(ROOT_DIR, "eval", "datasets", "eval_cases.json"),
)
OUTPUT_DIR = os.path.join(ROOT_DIR, "eval", "outputs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "eval_report.json")


@dataclass
class CaseResult:
    case_id: str
    case_type: str
    passed: bool
    score: float
    input_summary: str
    failures: List[str]
    actual: Dict[str, Any]
    category: str


class Evaluator:
    def __init__(self):
        self.engine = NutritionOrchestrator()

    def run_case(self, case: Dict[str, Any]) -> CaseResult:
        case_id = case["id"]
        case_type = case["type"]
        failures: List[str] = []

        history: List[Dict[str, str]] = []
        memory_entries: List[Any] = []
        conversation_memory: List[Dict[str, Any]] = []
        meal_state = MealState()

        last_response = None
        input_summary = ""
        category = self._extract_category(case_id)

        if case_type == "single_turn":
            user_input = case["input"]
            input_summary = user_input

            last_response = self.engine.run(
                user_input,
                history=history,
                memory_entries=memory_entries,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )
            self._save_turn(conversation_memory, user_input, last_response)

        elif case_type == "multi_turn":
            steps = case["steps"]
            input_summary = " -> ".join(steps)

            for step in steps:
                last_response = self.engine.run(
                    step,
                    history=history,
                    memory_entries=memory_entries,
                    meal_state=meal_state,
                    conversation_memory=conversation_memory,
                )
                self._save_turn(conversation_memory, step, last_response)

        else:
            failures.append(f"Unknown case type: {case_type}")

        expected = case.get("expected", {})
        actual = self._build_actual_payload(last_response, meal_state)

        score = self._evaluate_expected(expected, actual, failures)
        passed = len(failures) == 0

        return CaseResult(
            case_id=case_id,
            case_type=case_type,
            passed=passed,
            score=score,
            input_summary=input_summary,
            failures=failures,
            actual=actual,
            category=category,
        )

    def _extract_category(self, case_id: str) -> str:
        if not case_id:
            return "UNKNOWN"
        return case_id.split("-")[0].upper()

    def _save_turn(
        self,
        conversation_memory: List[Dict[str, Any]],
        user_input: str,
        response: Any,
    ) -> None:
        record: Dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_input": user_input,
            "normalized_input": (user_input or "").strip().lower(),
            "kind": getattr(response, "mode", "unknown"),
        }

        if hasattr(response, "answer"):
            record["answer"] = getattr(response, "answer", "")
            record["confidence"] = getattr(response, "confidence", "LOW")
            record["sources_used"] = getattr(response, "sources_used", []) or []
            record["retrieved_contexts"] = getattr(response, "retrieved_contexts", []) or []
            record["final_message"] = getattr(response, "final_message", "")

        if hasattr(response, "items"):
            items = []
            for item in getattr(response, "items", []) or []:
                items.append(
                    {
                        "input_food": getattr(item, "input_food", None),
                        "matched_food": getattr(item, "matched_food", None),
                        "grams": getattr(item, "grams", None),
                        "calories": getattr(item, "calories", None),
                        "kcal_per_100g": getattr(item, "kcal_per_100g", None),
                        "status": getattr(item, "status", None),
                        "confidence": getattr(item, "confidence", None),
                        "match_reason": getattr(item, "match_reason", None),
                        "match_source": getattr(item, "match_source", None),
                        "why_rejected": getattr(item, "why_rejected", None),
                        "suggestions": getattr(item, "suggestions", None),
                    }
                )
            record["items"] = items
            record["total_calories"] = getattr(response, "total_calories", None)
            record["final_message"] = getattr(response, "final_message", "")
            record["confidence"] = getattr(response, "confidence", "LOW")

        conversation_memory.append(record)

    def _build_actual_payload(self, response: Any, meal_state: MealState) -> Dict[str, Any]:
        if response is None:
            return {
                "mode": None,
                "answer": None,
                "final_message": None,
                "matched_items": None,
                "total_items": None,
                "total_calories": None,
                "meal_total": getattr(meal_state, "total_calories", 0),
                "confidence": None,
                "items_count": 0,
            }

        return {
            "mode": getattr(response, "mode", None),
            "answer": getattr(response, "answer", None),
            "final_message": getattr(response, "final_message", None),
            "confidence": getattr(response, "confidence", None),
            "matched_items": getattr(response, "matched_items", None),
            "total_items": getattr(response, "total_items", None),
            "total_calories": getattr(response, "total_calories", None),
            "meal_total": getattr(meal_state, "total_calories", 0),
            "items_count": len(getattr(response, "items", []) or []),
        }

    def _evaluate_expected(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        failures: List[str],
    ) -> float:
        checks = 0
        passed_checks = 0

        def check(condition: bool, message: str):
            nonlocal checks, passed_checks
            checks += 1
            if condition:
                passed_checks += 1
            else:
                failures.append(message)

        if "mode" in expected:
            check(
                actual["mode"] == expected["mode"],
                f"Expected mode={expected['mode']}, got {actual['mode']}",
            )

        if "final_mode" in expected:
            check(
                actual["mode"] == expected["final_mode"],
                f"Expected final_mode={expected['final_mode']}, got {actual['mode']}",
            )

        if "matched_items" in expected:
            check(
                actual["matched_items"] == expected["matched_items"],
                f"Expected matched_items={expected['matched_items']}, got {actual['matched_items']}",
            )

        if "total_items" in expected:
            check(
                actual["total_items"] == expected["total_items"],
                f"Expected total_items={expected['total_items']}, got {actual['total_items']}",
            )

        if "total_calories" in expected:
            check(
                self._approx_equal(actual["total_calories"], expected["total_calories"]),
                f"Expected total_calories≈{expected['total_calories']}, got {actual['total_calories']}",
            )

        if "meal_total" in expected:
            check(
                self._approx_equal(actual["meal_total"], expected["meal_total"]),
                f"Expected meal_total≈{expected['meal_total']}, got {actual['meal_total']}",
            )

        if "min_total_calories" in expected:
            check(
                actual["total_calories"] is not None
                and actual["total_calories"] >= expected["min_total_calories"],
                f"Expected total_calories >= {expected['min_total_calories']}, got {actual['total_calories']}",
            )

        if "max_total_calories" in expected:
            check(
                actual["total_calories"] is not None
                and actual["total_calories"] <= expected["max_total_calories"],
                f"Expected total_calories <= {expected['max_total_calories']}, got {actual['total_calories']}",
            )

        if "answer_contains" in expected:
            answer = (actual["answer"] or "").lower()
            needle = expected["answer_contains"].lower()
            check(
                needle in answer,
                f"Expected answer to contain '{needle}', got '{actual['answer']}'",
            )

        if expected.get("answer_nonempty") is True:
            answer = (actual["answer"] or "").strip()
            check(
                len(answer) > 0,
                "Expected non-empty answer, got empty answer",
            )

        if "final_message_contains" in expected:
            final_message = (actual["final_message"] or "").lower()
            needle = expected["final_message_contains"].lower()
            check(
                needle in final_message,
                f"Expected final_message to contain '{needle}', got '{actual['final_message']}'",
            )

        if "confidence_in" in expected:
            check(
                actual["confidence"] in expected["confidence_in"],
                f"Expected confidence in {expected['confidence_in']}, got {actual['confidence']}",
            )

        if checks == 0:
            return 0.0

        return round(passed_checks / checks, 4)

    def _approx_equal(self, a: Optional[float], b: Optional[float], tol: float = 1e-2) -> bool:
        if a is None or b is None:
            return False
        return math.isclose(float(a), float(b), abs_tol=tol)


def build_category_summary(results: List[CaseResult]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[CaseResult]] = defaultdict(list)

    for result in results:
        grouped[result.category].append(result)

    summary: Dict[str, Dict[str, Any]] = {}

    for category, items in sorted(grouped.items()):
        total = len(items)
        passed = sum(1 for r in items if r.passed)
        failed = total - passed
        avg_score = round(sum(r.score for r in items) / total, 4) if total else 0.0

        summary[category] = {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": failed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "average_score": avg_score,
        }

    return summary


def print_category_summary(category_summary: Dict[str, Dict[str, Any]]) -> None:
    print("\nCategory breakdown")
    print("=" * 70)
    print(f"{'Category':<12}{'Total':>8}{'Passed':>10}{'Failed':>10}{'Pass Rate':>14}{'Avg Score':>14}")
    print("-" * 70)

    for category, stats in category_summary.items():
        print(
            f"{category:<12}"
            f"{stats['total_cases']:>8}"
            f"{stats['passed_cases']:>10}"
            f"{stats['failed_cases']:>10}"
            f"{stats['pass_rate']:>14.2%}"
            f"{stats['average_score']:>14.2%}"
        )

    print("=" * 70)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found at: {DATASET_PATH}\n"
            f"Create it first or set EVAL_DATASET_PATH correctly."
        )

    if os.path.getsize(DATASET_PATH) == 0:
        raise ValueError(
            f"Dataset file is empty: {DATASET_PATH}\n"
            f"Generate the dataset before running evaluation."
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    evaluator = Evaluator()
    results: List[CaseResult] = []

    for case in cases:
        result = evaluator.run_case(case)
        results.append(result)

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.passed)
    failed_cases = total_cases - passed_cases
    avg_score = round(sum(r.score for r in results) / total_cases, 4) if total_cases else 0.0

    category_summary = build_category_summary(results)

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_path": DATASET_PATH,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": round(passed_cases / total_cases, 4) if total_cases else 0.0,
        "average_case_score": avg_score,
        "category_breakdown": category_summary,
    }

    output = {
        "summary": summary,
        "results": [asdict(r) for r in results],
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("Nutrition Assistant Evaluation Report")
    print("=" * 70)
    print(f"Dataset path    : {summary['dataset_path']}")
    print(f"Total cases     : {summary['total_cases']}")
    print(f"Passed cases    : {summary['passed_cases']}")
    print(f"Failed cases    : {summary['failed_cases']}")
    print(f"Pass rate       : {summary['pass_rate']:.2%}")
    print(f"Average score   : {summary['average_case_score']:.2%}")
    print(f"Report written  : {OUTPUT_PATH}")
    print("=" * 70)

    print_category_summary(category_summary)

    if failed_cases > 0:
        print("\nFailed cases:")
        for result in results:
            if not result.passed:
                print(f"- {result.case_id} [{result.category}]:")
                for failure in result.failures:
                    print(f"    * {failure}")


if __name__ == "__main__":
    main()