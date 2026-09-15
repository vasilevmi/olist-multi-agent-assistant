"""Маршрутизатор специализированных LLM-агентов."""

from typing import Any

from application.investigate.ports import AgentExecutor
from infrastructure.agents.delivery_agent import DeliveryAgent
from infrastructure.agents.reviews_agent import ReviewsAgent
from infrastructure.agents.sales_agent import SalesAgent
from infrastructure.agents.seller_agent import SellerAgent
from infrastructure.observability.run_metrics import RunMetrics


class MultiAgentExecutor(AgentExecutor):
    """Передаёт шаг orchestrator выбранному агенту."""

    def __init__(
        self,
        sales_agent: SalesAgent,
        seller_agent: SellerAgent,
        delivery_agent: DeliveryAgent,
        reviews_agent: ReviewsAgent,
        metrics: RunMetrics | None = None,
    ) -> None:
        self.metrics = metrics
        self.agents = {
            sales_agent.name: sales_agent,
            seller_agent.name: seller_agent,
            delivery_agent.name: delivery_agent,
            reviews_agent.name: reviews_agent,
        }

    def execute(
        self,
        agent_name: str,
        task: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Найти агента и передать ему шаг исследования."""

        agent = self.agents.get(agent_name)

        if agent is None:
            raise ValueError(
                f"Агент {agent_name} не зарегистрирован"
            )

        result = agent.execute(
            task=task,
            tool_name=tool_name,
            arguments=arguments,
        )

        if self.metrics is not None:
            self.metrics.record_tool_call()

        return result
