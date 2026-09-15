"""Запуск контрольного набора бизнес-кейсов."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from infrastructure.bootstrap import create_investigation_runtime


EVALUATION_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_CASES_FILE = EVALUATION_DIRECTORY / "cases.json"
DEFAULT_REPORTS_DIRECTORY = EVALUATION_DIRECTORY / "reports"


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Загрузить и проверить верхний уровень файла с кейсами."""

    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        raise ValueError("cases.json должен содержать список cases")
    return cases


def extract_path(value: Any, path: str) -> Any:
    """Получить вложенное значение по пути вида categories.0.name."""

    current = value
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def check_assertion(actual: Any, assertion: dict[str, Any]) -> bool:
    """Сравнить фактическое значение с одним ожидаемым условием."""

    operator = assertion.get("operator", "eq")
    expected = assertion.get("value")

    if operator == "eq":
        return actual == expected
    if operator == "approx":
        tolerance = float(assertion.get("tolerance", 0.01))
        return abs(float(actual) - float(expected)) <= tolerance
    if operator == "gt":
        return float(actual) > float(expected)
    if operator == "gte":
        return float(actual) >= float(expected)
    if operator == "contains":
        return expected in actual
    if operator == "length_gte":
        return len(actual) >= int(expected)
    raise ValueError(f"Неизвестный operator: {operator}")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Выполнить один вопрос и рассчитать его показатели качества."""

    runtime = create_investigation_runtime()
    investigation = runtime.use_case.execute(case["question"])
    runtime.metrics.finish()

    actual_tools = [item.tool_name for item in investigation.evidence]
    expected = case.get("expected", {})
    required_tools = expected.get("required_tools", [])
    required_groups = expected.get("required_tool_groups", [])
    forbidden_tools = expected.get("forbidden_tools", [])

    requirement_checks = [tool in actual_tools for tool in required_tools]
    requirement_checks.extend(
        any(tool in actual_tools for tool in group)
        for group in required_groups
    )
    evidence_coverage = (
        sum(requirement_checks) / len(requirement_checks)
        if requirement_checks
        else 1.0
    )
    tool_selection_passed = (
        evidence_coverage == 1.0
        and not any(tool in actual_tools for tool in forbidden_tools)
    )

    evidence_by_tool = {
        item.tool_name: item.data for item in investigation.evidence
    }
    assertion_results: list[dict[str, Any]] = []

    for assertion in expected.get("assertions", []):
        passed = False
        actual: Any = None
        error: str | None = None
        try:
            tool_data = evidence_by_tool[assertion["tool"]]
            actual = extract_path(tool_data, assertion["path"])
            passed = check_assertion(actual, assertion)
        except Exception as exception:
            error = str(exception)

        assertion_results.append(
            {
                "tool": assertion["tool"],
                "path": assertion["path"],
                "operator": assertion.get("operator", "eq"),
                "expected": assertion.get("value"),
                "actual": actual,
                "passed": passed,
                "error": error,
            }
        )

    factual_accuracy = (
        sum(item["passed"] for item in assertion_results)
        / len(assertion_results)
        if assertion_results
        else None
    )

    known_evidence_ids = {
        item.evidence_id for item in investigation.evidence
    }
    grounding_checks = [
        bool(finding.evidence_ids)
        and set(finding.evidence_ids).issubset(known_evidence_ids)
        for finding in investigation.findings
    ]
    evidence_grounding_passed = bool(grounding_checks) and all(
        grounding_checks
    )
    structured_answer_passed = bool(
        investigation.short_summary
        and investigation.main_factors
        and investigation.conclusion
    )
    completed = investigation.status.value == "completed"
    assertions_passed = factual_accuracy in {None, 1.0}
    passed = all(
        (
            completed,
            tool_selection_passed,
            assertions_passed,
            evidence_grounding_passed,
            structured_answer_passed,
        )
    )

    return {
        "id": case["id"],
        "type": case["type"],
        "question": case["question"],
        "passed": passed,
        "status": investigation.status.value,
        "error_message": investigation.error_message,
        "actual_tools": actual_tools,
        "tool_selection_passed": tool_selection_passed,
        "evidence_coverage": round(evidence_coverage, 4),
        "factual_accuracy": (
            round(factual_accuracy, 4)
            if factual_accuracy is not None
            else None
        ),
        "assertions": assertion_results,
        "evidence_grounding_passed": evidence_grounding_passed,
        "structured_answer_passed": structured_answer_passed,
        "answer": {
            "short_summary": investigation.short_summary,
            "main_factors": investigation.main_factors,
            "conclusion": investigation.conclusion,
            "next_checks": investigation.next_checks,
        },
        "metrics": {
            "llm_calls": runtime.metrics.llm_calls,
            "planning_calls": runtime.metrics.planning_calls,
            "tool_calls": runtime.metrics.tool_calls,
            "duration_seconds": round(runtime.metrics.duration_seconds, 3),
        },
    }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Собрать итоговые метрики всего контрольного набора."""

    total = len(results)
    factual_results = [
        result["factual_accuracy"]
        for result in results
        if result["factual_accuracy"] is not None
    ]

    def average(field: str) -> float:
        return round(
            sum(result["metrics"][field] for result in results) / total,
            3,
        ) if total else 0.0

    return {
        "total_cases": total,
        "passed_cases": sum(result["passed"] for result in results),
        "case_success_rate": round(
            sum(result["passed"] for result in results) / total,
            4,
        ) if total else 0.0,
        "factual_accuracy": round(
            sum(factual_results) / len(factual_results),
            4,
        ) if factual_results else None,
        "average_evidence_coverage": round(
            sum(result["evidence_coverage"] for result in results) / total,
            4,
        ) if total else 0.0,
        "tool_selection_error_rate": round(
            sum(not result["tool_selection_passed"] for result in results)
            / total,
            4,
        ) if total else 0.0,
        "evidence_grounding_rate": round(
            sum(result["evidence_grounding_passed"] for result in results)
            / total,
            4,
        ) if total else 0.0,
        "structured_answer_rate": round(
            sum(result["structured_answer_passed"] for result in results)
            / total,
            4,
        ) if total else 0.0,
        "average_tool_calls": average("tool_calls"),
        "average_llm_calls": average("llm_calls"),
        "average_latency_seconds": average("duration_seconds"),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluation системы Olist")
    parser.add_argument("--cases-file", type=Path, default=DEFAULT_CASES_FILE)
    parser.add_argument("--type", choices=["deterministic", "research"])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    cases = load_cases(args.cases_file)

    if args.type:
        cases = [case for case in cases if case["type"] == args.type]
    if args.case_id:
        selected_ids = set(args.case_id)
        cases = [case for case in cases if case["id"] in selected_ids]
    if args.limit is not None:
        cases = cases[: args.limit]

    if args.list:
        for case in cases:
            print(f"{case['id']} [{case['type']}] {case['question']}")
        return

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}: {case['question']}")
        result = evaluate_case(case)
        results.append(result)
        marker = "PASS" if result["passed"] else "FAIL"
        print(
            f"  {marker}; tools={result['actual_tools']}; "
            f"time={result['metrics']['duration_seconds']:.2f}s"
        )

    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "cases_file": str(args.cases_file),
        "summary": build_summary(results),
        "results": results,
    }

    output_path = args.output
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_REPORTS_DIRECTORY / f"report_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nИтог:")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"\nОтчёт: {output_path}")


if __name__ == "__main__":
    main()
