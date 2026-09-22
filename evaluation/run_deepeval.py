"""Понятный последовательный запуск DeepEval с отчётами JSON и Markdown."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, DisplayConfig, ErrorConfig

from domain.investigation.entities import InvestigationStatus
from evaluation.deepeval_suite.adapter import to_deepeval_test_case
from evaluation.deepeval_suite.judge import create_deepeval_judge
from evaluation.deepeval_suite.metrics import build_metrics
from evaluation.deepeval_suite.test_agents import load_cases, run_application


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "evaluation" / "reports"
JSON_REPORT = REPORTS_DIR / "deepeval_results.json"
MARKDOWN_REPORT = REPORTS_DIR / "deepeval_results.md"


def parse_arguments() -> argparse.Namespace:
    """Прочитать фильтры контрольного запуска."""

    parser = argparse.ArgumentParser(
        description="Запустить DeepEval и сохранить понятный отчёт.",
    )
    parser.add_argument(
        "--case",
        dest="case_id",
        help="Запустить один кейс, например D001.",
    )
    parser.add_argument(
        "--mark",
        choices=("deterministic", "research"),
        help="Запустить только выбранный тип кейсов.",
    )
    return parser.parse_args()


def select_cases(arguments: argparse.Namespace) -> list[dict[str, Any]]:
    """Выбрать кейсы с учётом аргументов командной строки."""

    cases = load_cases()

    if arguments.case_id:
        requested_id = arguments.case_id.upper()
        cases = [
            case
            for case in cases
            if str(case.get("id", "")).upper() == requested_id
        ]

    if arguments.mark:
        cases = [
            case
            for case in cases
            if case.get("type") == arguments.mark
        ]

    if not cases:
        raise ValueError("По заданным фильтрам не найдено ни одного кейса")

    return cases


def metric_record(metric: Any) -> dict[str, Any]:
    """Преобразовать результат одной метрики DeepEval в JSON."""

    return {
        "name": getattr(metric, "name", "unknown"),
        "passed": getattr(metric, "success", None),
        "score": getattr(metric, "score", None),
        "threshold": getattr(metric, "threshold", None),
        "reason": getattr(metric, "reason", None),
        "error": getattr(metric, "error", None),
        "evaluation_model": getattr(metric, "evaluation_model", None),
        "evaluation_cost": getattr(metric, "evaluation_cost", None),
    }


def markdown_text(value: Any) -> str:
    """Подготовить значение для одной ячейки Markdown-таблицы."""

    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    """Создать человекочитаемый отчёт."""

    summary = report["summary"]
    lines = [
        "# Отчёт DeepEval",
        "",
        f"- Начало: {report['started_at']}",
        f"- Завершение: {report.get('finished_at') or 'прогон продолжается'}",
        f"- Всего кейсов: {summary['total']}",
        f"- Выполнено: {summary['completed']}",
        f"- Пройдено: {summary['passed']}",
        f"- Не пройдено: {summary['failed']}",
        "",
    ]

    for case in report["cases"]:
        status = "PASSED" if case["passed"] else "FAILED"
        lines.extend(
            [
                f"## {case['id']} — {status}",
                "",
                f"**Вопрос:** {case['question']}",
                "",
                f"**Время приложения:** {case.get('duration_seconds', 0):.3f} с",
                "",
            ]
        )

        if case.get("error"):
            lines.extend([f"**Ошибка:** {case['error']}", ""])

        metrics = case.get("metrics", [])
        if metrics:
            lines.extend(
                [
                    "| Метрика | Оценка | Порог | Статус | Причина | Ошибка |",
                    "|---|---:|---:|---|---|---|",
                ]
            )
            for metric in metrics:
                metric_status = "PASSED" if metric["passed"] else "FAILED"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            markdown_text(metric["name"]),
                            markdown_text(metric["score"]),
                            markdown_text(metric["threshold"]),
                            metric_status,
                            markdown_text(metric["reason"]),
                            markdown_text(metric["error"]),
                        ]
                    )
                    + " |"
                )
            lines.append("")

    return "\n".join(lines) + "\n"


def save_report(report: dict[str, Any]) -> None:
    """Сохранить отчёт после каждого кейса."""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    MARKDOWN_REPORT.write_text(
        render_markdown(report),
        encoding="utf-8",
    )


def evaluate_case(case: dict[str, Any], position: int, total: int) -> dict[str, Any]:
    """Запустить приложение и оценить один кейс через DeepEval."""

    case_id = str(case.get("id", "unknown"))
    question = str(case.get("question", ""))
    print(f"[{position}/{total}] {case_id}: {question}", flush=True)

    try:
        investigation, duration = asyncio.run(run_application(case))
    except Exception as error:
        return {
            "id": case_id,
            "type": case.get("type"),
            "question": question,
            "passed": False,
            "duration_seconds": 0.0,
            "error": f"Ошибка запуска приложения: {error}",
            "metrics": [],
        }

    if investigation.status is not InvestigationStatus.COMPLETED:
        return {
            "id": case_id,
            "type": case.get("type"),
            "question": question,
            "passed": False,
            "duration_seconds": duration,
            "error": investigation.error_message or "Исследование не завершено",
            "metrics": [],
        }

    test_case = to_deepeval_test_case(
        investigation=investigation,
        case=case,
        completion_time=duration,
    )
    judge = create_deepeval_judge()
    metrics = build_metrics(
        judge,
        research=case.get("type") == "research",
    )

    try:
        result = evaluate(
            test_cases=[test_case],
            metrics=metrics,
            async_config=AsyncConfig(
                run_async=True,
                max_concurrent=4,
            ),
            display_config=DisplayConfig(
                show_indicator=False,
                print_results=False,
                inspect_after_run=False,
            ),
            error_config=ErrorConfig(ignore_errors=True),
        )
        test_result = result.test_results[0]
        metric_results = [
            metric_record(metric)
            for metric in (test_result.metrics_data or [])
        ]
        passed = bool(test_result.success) and all(
            metric.get("passed") is True
            for metric in metric_results
        )
        error = None
    except Exception as evaluation_error:
        metric_results = []
        passed = False
        error = f"Ошибка DeepEval: {evaluation_error}"

    return {
        "id": case_id,
        "type": case.get("type"),
        "question": question,
        "passed": passed,
        "duration_seconds": duration,
        "error": error,
        "actual_output": test_case.actual_output,
        "tools_called": [tool.name for tool in test_case.tools_called or []],
        "metrics": metric_results,
    }


def run() -> int:
    """Последовательно выполнить выбранные кейсы."""

    arguments = parse_arguments()
    cases = select_cases(arguments)
    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": None,
        "summary": {
            "total": len(cases),
            "completed": 0,
            "passed": 0,
            "failed": 0,
        },
        "cases": [],
    }
    save_report(report)

    for position, case in enumerate(cases, start=1):
        result = evaluate_case(case, position, len(cases))
        report["cases"].append(result)
        report["summary"]["completed"] += 1
        if result["passed"]:
            report["summary"]["passed"] += 1
            print("  PASSED", flush=True)
        else:
            report["summary"]["failed"] += 1
            print(
                f"  FAILED: {result.get('error') or 'см. оценки метрик'}",
                flush=True,
            )
        save_report(report)

    report["finished_at"] = datetime.now(UTC).isoformat()
    save_report(report)

    summary = report["summary"]
    print()
    print(
        "Готово: "
        f"{summary['passed']} passed, {summary['failed']} failed, "
        f"всего {summary['total']}."
    )
    print(f"JSON: {JSON_REPORT}")
    print(f"Markdown: {MARKDOWN_REPORT}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
