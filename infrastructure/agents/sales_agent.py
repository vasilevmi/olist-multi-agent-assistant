"""LLM-агент продаж, товаров и категорий."""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.mcp.catalog_server import (
    get_category,
    get_category_products,
    get_product,
    get_product_statistics,
)
from infrastructure.mcp.sales_server import (
    compare_sellers,
    get_order_by_id,
    get_category_sales_ranking,
    get_sales_by_category,
    get_sales_by_period,
    get_sales_summary,
    get_seller_sales,
    get_top_sellers,
)


class SalesAgent:
    """Проверяет шаг orchestrator и вызывает инструменты продаж."""

    name = "sales_agent"

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

        self.tools: dict[
            str,
            Callable[..., BaseModel],
        ] = {
            "get_order_by_id": get_order_by_id,
            "get_sales_summary": get_sales_summary,
            "get_sales_by_period": get_sales_by_period,
            "get_sales_by_category": get_sales_by_category,
            "get_category_sales_ranking": (
                get_category_sales_ranking
            ),
            "get_seller_sales": get_seller_sales,
            "get_top_sellers": get_top_sellers,
            "compare_sellers": compare_sellers,
            "get_product": get_product,
            "get_category": get_category,
            "get_category_products": get_category_products,
            "get_product_statistics": get_product_statistics,
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
                f"SalesAgent не имеет инструмента {tool_name}"
            )

        request_data = {
            "task": task,
            "tool_name": tool_name,
            "arguments": arguments,
        }

        decision = self.client.generate_json(
            system_prompt=(
                "Ты Sales Agent системы Olist. "
                "Ты отвечаешь только за продажи, выручку, "
                "товары и категории. Проверь, подходит ли "
                "выбранный инструмент для поставленной задачи. "
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
                f"SalesAgent отклонил шаг: {reason}"
            )

        tool = self.tools[tool_name]

        result = tool(**arguments)

        return result.model_dump(mode="json")
