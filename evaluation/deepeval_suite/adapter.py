"""Преобразование результата Olist в стандартный тест-кейс DeepEval."""

import json
from typing import Any

from deepeval.test_case import LLMTestCase, ToolCall

from domain.investigation.entities import Investigation


def _actual_tool_calls(investigation: Investigation) -> list[ToolCall]:
    """Представить выполненные MCP-вызовы в формате DeepEval."""

    calls: list[ToolCall] = []

    for step in investigation.steps:
        if step.tool_name is None:
            continue

        calls.append(
            ToolCall(
                name=step.tool_name,
                input_parameters=step.arguments,
                output=step.result,
            )
        )

    return calls


def _expected_tool_calls(case: dict[str, Any]) -> list[ToolCall]:
    """Прочитать обязательные инструменты из Gold Dataset."""

    expected = case.get("expected", {})
    required_tools = expected.get("required_tools", [])

    if not isinstance(required_tools, list):
        return []

    return [
        ToolCall(name=str(tool_name))
        for tool_name in required_tools
    ]


def _evidence_context(investigation: Investigation) -> list[str]:
    """Подготовить фактический контекст для проверки groundedness."""

    return [
        json.dumps(
            {
                "evidence_id": evidence.evidence_id,
                "source": evidence.source,
                "tool_name": evidence.tool_name,
                "data": evidence.data,
            },
            ensure_ascii=False,
            default=str,
        )
        for evidence in investigation.evidence
    ]


def _expected_output(case: dict[str, Any]) -> str:
    """Преобразовать Gold Dataset в эталонные требования для LLM-судьи."""

    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        expected = {}

    requirements: list[str] = []

    for assertion in expected.get("assertions", []):
        if not isinstance(assertion, dict):
            continue

        requirements.append(
            "В результате инструмента "
            f"{assertion.get('tool')} значение по пути "
            f"{assertion.get('path')} должно удовлетворять условию "
            f"{assertion.get('operator', 'eq')} "
            f"{assertion.get('value')}"
            + (
                f" с допуском {assertion.get('tolerance')}"
                if "tolerance" in assertion
                else ""
            )
            + "."
        )

    required_tools = expected.get("required_tools", [])
    if required_tools:
        requirements.append(
            "Ответ должен опираться на Evidence от инструментов: "
            + ", ".join(map(str, required_tools))
            + "."
        )

    for group in expected.get("required_tool_groups", []):
        if isinstance(group, list) and group:
            requirements.append(
                "Должен быть использован хотя бы один инструмент из группы: "
                + ", ".join(map(str, group))
                + "."
            )

    forbidden_tools = expected.get("forbidden_tools", [])
    if forbidden_tools:
        requirements.append(
            "Не следует использовать инструменты: "
            + ", ".join(map(str, forbidden_tools))
            + "."
        )

    return " ".join(requirements) or (
        "Ответ должен корректно и полно отвечать на вопрос только по Evidence."
    )


def _actual_output(investigation: Investigation) -> str:
    """Собрать полный пользовательский ответ для оценки DeepEval.

    В интерфейсе ответ состоит не только из краткого вывода, но и из основных
    факторов и следующих проверок. Если оценивать один short_summary, метрики
    полноты и релевантности не видят значительную часть настоящего ответа.
    """

    primary_answer = (
        investigation.short_summary
        or investigation.final_answer
        or investigation.error_message
        or "Система не вернула ответ"
    )
    sections = [f"Краткий ответ:\n{primary_answer}"]

    if investigation.main_factors:
        factors = "\n".join(
            f"- {factor}"
            for factor in investigation.main_factors
            if str(factor).strip()
        )
        if factors:
            sections.append(f"Основные факторы:\n{factors}")

    if investigation.next_checks:
        checks = "\n".join(
            f"- {check}"
            for check in investigation.next_checks
            if str(check).strip()
        )
        if checks:
            sections.append(f"Что проверить дальше:\n{checks}")

    return "\n\n".join(sections)


def to_deepeval_test_case(
    investigation: Investigation,
    case: dict[str, Any],
    *,
    completion_time: float | None = None,
) -> LLMTestCase:
    """Создать LLMTestCase для end-to-end оценки исследования."""

    return LLMTestCase(
        name=str(case.get("id", investigation.investigation_id)),
        input=str(case.get("question", investigation.question)),
        actual_output=_actual_output(investigation),
        expected_output=_expected_output(case),
        retrieval_context=_evidence_context(investigation),
        tools_called=_actual_tool_calls(investigation),
        expected_tools=_expected_tool_calls(case),
        completion_time=completion_time,
        tags=[str(case.get("type", "unknown")), "olist"],
    )
