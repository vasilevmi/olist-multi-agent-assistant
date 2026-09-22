"""Инструменты делегирования специализированным LangChain-агентам."""

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool, tool


def _serialize_agent_result(result: dict[str, Any]) -> str:
    """Вернуть итог агента вместе с результатами его инструментов."""

    messages = result.get("messages", [])
    final_answer: Any = ""
    evidence: list[dict[str, Any]] = []
    tool_calls: dict[str, dict[str, Any]] = {}

    if messages:
        final_answer = messages[-1].content

    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                call_id = tool_call.get("id")
                if isinstance(call_id, str):
                    tool_calls[call_id] = tool_call

    for message in messages:
        if isinstance(message, ToolMessage):
            tool_call = tool_calls.get(message.tool_call_id, {})
            arguments = tool_call.get("args", {})
            if not isinstance(arguments, dict):
                arguments = {}

            evidence.append(
                {
                    "tool_name": message.name,
                    "arguments": arguments,
                    "content": message.content,
                    "status": message.status,
                }
            )

    return json.dumps(
        {
            "answer": final_answer,
            "evidence": evidence,
        },
        ensure_ascii=False,
        default=str,
    )


def create_delegation_tools(
    sales_agent: Runnable,
    seller_agent: Runnable,
    delivery_agent: Runnable,
    reviews_agent: Runnable,
) -> list[BaseTool]:
    """Представить специализированных агентов как инструменты Orchestrator."""

    @tool("ask_sales_agent")
    async def ask_sales_agent(
        task: str,
        config: RunnableConfig,
    ) -> str:
        """Исследовать продажи, заказы, выручку, товары или категории."""

        result = await sales_agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return _serialize_agent_result(result)

    @tool("ask_seller_agent")
    async def ask_seller_agent(
        task: str,
        config: RunnableConfig,
    ) -> str:
        """Исследовать продавца, его местоположение и ассортимент."""

        result = await seller_agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return _serialize_agent_result(result)

    @tool("ask_delivery_agent")
    async def ask_delivery_agent(
        task: str,
        config: RunnableConfig,
    ) -> str:
        """Исследовать сроки, задержки и регионы доставки."""

        result = await delivery_agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return _serialize_agent_result(result)

    @tool("ask_reviews_agent")
    async def ask_reviews_agent(
        task: str,
        config: RunnableConfig,
    ) -> str:
        """Исследовать отзывы, оценки и клиентский опыт."""

        result = await reviews_agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
        )
        return _serialize_agent_result(result)

    return [
        ask_sales_agent,
        ask_seller_agent,
        ask_delivery_agent,
        ask_reviews_agent,
    ]
