"""LLM-агент анализа отзывов и оценок."""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.mcp.reviews_server import (
    analyze_delivery_rating_relationship,
    get_category_negative_review_ranking,
    get_category_rating,
    get_category_rating_ranking,
    get_negative_reviews,
    get_product_review_summary,
    get_rating_distribution,
    get_review_statistics,
    get_seller_rating,
    get_seller_negative_reviews,
)


class ReviewsAgent:
    """Проверяет шаг orchestrator и вызывает инструменты отзывов."""

    name = "reviews_agent"

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

        self.tools: dict[
            str,
            Callable[..., BaseModel],
        ] = {
            "analyze_delivery_rating_relationship": (
                analyze_delivery_rating_relationship
            ),
            "get_review_statistics": get_review_statistics,
            "get_seller_rating": get_seller_rating,
            "get_category_rating": get_category_rating,
            "get_category_rating_ranking": (
                get_category_rating_ranking
            ),
            "get_category_negative_review_ranking": (
                get_category_negative_review_ranking
            ),
            "get_product_review_summary": (
                get_product_review_summary
            ),
            "get_negative_reviews": get_negative_reviews,
            "get_seller_negative_reviews": (
                get_seller_negative_reviews
            ),
            "get_rating_distribution": (
                get_rating_distribution
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
                f"ReviewsAgent не имеет инструмента {tool_name}"
            )

        request_data = {
            "task": task,
            "tool_name": tool_name,
            "arguments": arguments,
        }

        decision = self.client.generate_json(
            system_prompt=(
                "Ты Reviews Agent системы Olist. "
                "Ты отвечаешь только за отзывы, оценки, "
                "негативные отзывы и распределение рейтинга. "
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
                f"ReviewsAgent отклонил шаг: {reason}"
            )

        tool = self.tools[tool_name]

        result = tool(**arguments)

        return result.model_dump(mode="json")
