"""LLM-агент информации о продавцах."""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.mcp.seller_server import (
    find_high_sales_low_rating_sellers,
    get_seller,
    get_seller_catalog,
    get_seller_top_products,
    get_sellers_by_location,
)


class SellerAgent:
    """Проверяет шаг orchestrator и вызывает инструменты продавцов."""

    name = "seller_agent"

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

        self.tools: dict[
            str,
            Callable[..., BaseModel],
        ] = {
            "get_seller": get_seller,
            "get_sellers_by_location": get_sellers_by_location,
            "get_seller_catalog": get_seller_catalog,
            "get_seller_top_products": get_seller_top_products,
            "find_high_sales_low_rating_sellers": (
                find_high_sales_low_rating_sellers
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
                f"SellerAgent не имеет инструмента {tool_name}"
            )

        request_data = {
            "task": task,
            "tool_name": tool_name,
            "arguments": arguments,
        }

        decision = self.client.generate_json(
            system_prompt=(
                "Ты Seller Agent системы Olist. "
                "Ты отвечаешь за информацию о продавцах, "
                "их местоположение, ассортимент, лучшие товары и "
                "комплексные показатели продавцов. "
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
                f"SellerAgent отклонил шаг: {reason}"
            )

        tool = self.tools[tool_name]

        result = tool(**arguments)

        return result.model_dump(mode="json")
