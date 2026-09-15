"""LLM-агент анализа доставки."""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.mcp.delivery_server import (
    find_sellers_by_delay_rate,
    get_category_delivery_ranking,
    get_delayed_orders,
    get_delivery_by_order_id,
    get_delivery_by_region,
    get_region_delivery_ranking,
    get_delivery_statistics,
    get_seller_average_delivery_time,
    get_seller_delivery_performance,
)


class DeliveryAgent:
    """Проверяет шаг orchestrator и вызывает инструменты доставки."""

    name = "delivery_agent"

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

        self.tools: dict[
            str,
            Callable[..., BaseModel],
        ] = {
            "get_delivery_by_order_id": (
                get_delivery_by_order_id
            ),
            "get_delivery_statistics": (
                get_delivery_statistics
            ),
            "get_delayed_orders": get_delayed_orders,
            "get_seller_delivery_performance": (
                get_seller_delivery_performance
            ),
            "find_sellers_by_delay_rate": (
                find_sellers_by_delay_rate
            ),
            "get_seller_average_delivery_time": (
                get_seller_average_delivery_time
            ),
            "get_delivery_by_region": (
                get_delivery_by_region
            ),
            "get_category_delivery_ranking": (
                get_category_delivery_ranking
            ),
            "get_region_delivery_ranking": (
                get_region_delivery_ranking
            ),
        }

    def execute(
        self,
        task: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Проверить и выполнить один шаг исследования."""

        if tool_name not in self.tools:
            raise ValueError(
                f"DeliveryAgent не имеет инструмента {tool_name}"
            )

        request_data = {
            "task": task,
            "tool_name": tool_name,
            "arguments": arguments,
        }

        decision = self.client.generate_json(
            system_prompt=(
                "Ты Delivery Agent системы Olist. "
                "Ты отвечаешь только за сроки доставки, "
                "задержки, ожидаемые даты и регионы покупателей. "
                "Проверь, подходит ли выбранный инструмент "
                "для поставленной задачи. "
                "Не придумывай новые значения аргументов. "
                "Верни только JSON формата: "
                '{"approved": true, "reason": "объяснение"}.'
            ),
            user_prompt=json.dumps(
                request_data,
                ensure_ascii=False,
            ),
            max_tokens=300,
        )

        if decision.get("approved") is not True:
            reason = decision.get(
                "reason",
                "причина не указана",
            )

            raise ValueError(
                f"DeliveryAgent отклонил шаг: {reason}"
            )

        tool = self.tools[tool_name]

        result = tool(**arguments)

        return result.model_dump(mode="json")
