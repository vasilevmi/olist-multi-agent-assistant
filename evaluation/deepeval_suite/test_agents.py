"""End-to-end тесты мультиагентной системы через DeepEval."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from deepeval import assert_test

from domain.investigation.entities import InvestigationStatus
from evaluation.deepeval_suite.adapter import to_deepeval_test_case
from evaluation.deepeval_suite.judge import create_deepeval_judge
from evaluation.deepeval_suite.metrics import build_metrics
from infrastructure.bootstrap import create_investigation_runtime


CASES_FILE = Path(__file__).resolve().parents[1] / "cases.json"


def load_cases() -> list[dict[str, Any]]:
    """Загрузить контрольный набор из cases.json."""

    payload = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None

    if not isinstance(cases, list):
        raise ValueError("cases.json должен содержать список cases")

    return [case for case in cases if isinstance(case, dict)]


def case_parameters() -> list[Any]:
    """Создать pytest-параметры с ID и типом каждого кейса."""

    parameters: list[Any] = []

    for case in load_cases():
        case_id = str(case.get("id", "unknown"))
        case_type = str(case.get("type", "unknown"))
        marker = (
            pytest.mark.research
            if case_type == "research"
            else pytest.mark.deterministic
        )
        parameters.append(
            pytest.param(
                case,
                id=case_id,
                marks=marker,
            )
        )

    return parameters


async def run_application(case: dict[str, Any]):
    """Получить настоящий ответ системы для одного контрольного кейса."""

    question = case.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("У evaluation-кейса отсутствует question")

    runtime = await create_investigation_runtime()

    try:
        investigation = await runtime.use_case.execute(question.strip())
    finally:
        runtime.metrics.finish()

    return investigation, runtime.metrics.duration_seconds


@pytest.mark.parametrize("case", case_parameters())
def test_agent_case(case: dict[str, Any]) -> None:
    """Запустить приложение и передать результат готовым метрикам DeepEval."""

    investigation, duration = asyncio.run(run_application(case))

    if investigation.status is not InvestigationStatus.COMPLETED:
        pytest.fail(
            "Приложение не завершило исследование: "
            f"{investigation.error_message or 'причина не указана'}"
        )

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

    assert_test(
        test_case,
        metrics,
        run_async=True,
    )
