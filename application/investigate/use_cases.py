"""Сценарий исследования вопроса через LangChain-агентов."""

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig

from domain.investigation.entities import ConfidenceLevel, Investigation
from infrastructure.agents.evidence_critic import CriticResponse


DELEGATION_AGENTS = {
    "ask_sales_agent": "sales_agent",
    "ask_seller_agent": "seller_agent",
    "ask_delivery_agent": "delivery_agent",
    "ask_reviews_agent": "reviews_agent",
}


def _as_dictionary(value: Any) -> dict[str, Any]:
    """Преобразовать JSON-ответ инструмента в обычный словарь."""

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"value": value}

        if isinstance(parsed, dict):
            return parsed

        return {"value": parsed}

    return {"value": value}


def _find_delegation_calls(messages: list[Any]) -> dict[str, dict[str, Any]]:
    """Связать ID вызова delegation tool с его именем и аргументами."""

    calls: dict[str, dict[str, Any]] = {}

    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        for tool_call in message.tool_calls:
            call_id = tool_call.get("id")
            if isinstance(call_id, str):
                calls[call_id] = tool_call

    return calls


class InvestigateQuestion:
    """Выполнить исследование и вернуть доменный объект Investigation."""

    def __init__(
        self,
        orchestrator: Runnable,
        critic: Runnable,
    ) -> None:
        self.orchestrator = orchestrator
        self.critic = critic

    async def execute(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        config: RunnableConfig | None = None,
    ) -> Investigation:
        """Запустить Orchestrator, собрать Evidence и вызвать Critic."""

        investigation = Investigation(question=question)
        investigation.start()
        limitations: list[str] = []

        input_messages: list[dict[str, str]] = list(history or [])
        input_messages.append(
            {"role": "user", "content": investigation.question}
        )

        try:
            orchestration_result = await self.orchestrator.ainvoke(
                {"messages": input_messages},
                config=config,
            )
        except Exception as error:
            investigation.fail(
                f"Не удалось выполнить исследование: {error}"
            )
            return investigation

        messages = orchestration_result.get("messages", [])
        delegation_calls = _find_delegation_calls(messages)

        for message in messages:
            if not isinstance(message, ToolMessage):
                continue

            delegation_name = message.name or ""
            if delegation_name not in DELEGATION_AGENTS:
                continue

            call = delegation_calls.get(message.tool_call_id, {})
            arguments = call.get("args", {})
            if not isinstance(arguments, dict):
                arguments = {}

            task = arguments.get("task")
            if not isinstance(task, str) or not task.strip():
                task = f"Задача для {delegation_name}"

            agent_name = DELEGATION_AGENTS[delegation_name]
            delegation_result = _as_dictionary(message.content)
            raw_evidence = delegation_result.get("evidence", [])

            if not isinstance(raw_evidence, list) or not raw_evidence:
                limitations.append(
                    f"{agent_name} не вернул результатов MCP-инструментов"
                )
                continue

            for raw_item in raw_evidence:
                if not isinstance(raw_item, dict):
                    continue

                tool_name = str(raw_item.get("tool_name") or "unknown")
                tool_status = str(raw_item.get("status") or "success")
                tool_data = _as_dictionary(raw_item.get("content"))
                tool_arguments = raw_item.get("arguments", {})
                if not isinstance(tool_arguments, dict):
                    tool_arguments = {}

                step = investigation.add_step(
                    description=task,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    arguments=tool_arguments,
                )
                step.start()

                if tool_status == "error":
                    error_message = str(
                        tool_data.get("value", "MCP-инструмент вернул ошибку")
                    )
                    step.fail(error_message)
                    limitations.append(
                        f"Не удалось выполнить {tool_name}: {error_message}"
                    )
                    continue

                step.complete(tool_data)
                investigation.add_evidence(
                    source=agent_name,
                    tool_name=tool_name,
                    data=tool_data,
                )

        if not investigation.evidence:
            investigation.fail(
                "Orchestrator не получил Evidence от MCP-инструментов"
            )
            return investigation

        critic_input = {
            "question": investigation.question,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "source": item.source,
                    "tool_name": item.tool_name,
                    "data": item.data,
                }
                for item in investigation.evidence
            ],
            "limitations": limitations,
        }

        try:
            critic_result = await self.critic.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": json.dumps(
                                critic_input,
                                ensure_ascii=False,
                                default=str,
                            ),
                        }
                    ]
                },
                config=config,
            )
            analysis = critic_result.get("structured_response")
            if not isinstance(analysis, CriticResponse):
                raise TypeError("Critic не вернул CriticResponse")
        except Exception as error:
            investigation.fail(
                f"Не удалось проверить собранные Evidence: {error}"
            )
            return investigation

        known_evidence_ids = {
            item.evidence_id for item in investigation.evidence
        }

        for finding in analysis.findings:
            valid_ids = [
                evidence_id
                for evidence_id in finding.evidence_ids
                if evidence_id in known_evidence_ids
            ]

            if not finding.is_hypothesis and not valid_ids:
                continue

            investigation.add_finding(
                statement=finding.statement,
                evidence_ids=valid_ids,
                confidence=ConfidenceLevel(finding.confidence),
                is_hypothesis=finding.is_hypothesis,
            )

        investigation.complete(
            final_answer=analysis.short_summary,
            short_summary=analysis.short_summary,
            main_factors=analysis.main_factors,
            conclusion=analysis.conclusion,
            next_checks=analysis.next_checks,
        )

        return investigation
