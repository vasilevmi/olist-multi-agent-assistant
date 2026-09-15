"""Сборка компонентов приложения в единый рабочий сценарий."""

from dataclasses import dataclass

from application.investigate.use_cases import InvestigateQuestion
from infrastructure.agents.delivery_agent import DeliveryAgent
from infrastructure.agents.evidence_critic import LLMEvidenceCritic
from infrastructure.agents.orchestrator import LLMOrchestrator
from infrastructure.agents.reviews_agent import ReviewsAgent
from infrastructure.agents.sales_agent import SalesAgent
from infrastructure.agents.seller_agent import SellerAgent
from infrastructure.execution.multi_agent_executor import MultiAgentExecutor
from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.observability.run_metrics import RunMetrics


@dataclass
class InvestigationRuntime:
    """Готовый сценарий исследования и его счётчик метрик."""

    use_case: InvestigateQuestion
    metrics: RunMetrics


def create_investigation_runtime() -> InvestigationRuntime:
    """Создать независимый набор компонентов для одного запроса."""

    metrics = RunMetrics()
    llm_client = OpenAICompatibleClient.from_env(metrics=metrics)

    orchestrator = LLMOrchestrator(
        client=llm_client,
        metrics=metrics,
    )

    sales_agent = SalesAgent(client=llm_client)
    seller_agent = SellerAgent(client=llm_client)
    delivery_agent = DeliveryAgent(client=llm_client)
    reviews_agent = ReviewsAgent(client=llm_client)

    executor = MultiAgentExecutor(
        sales_agent=sales_agent,
        seller_agent=seller_agent,
        delivery_agent=delivery_agent,
        reviews_agent=reviews_agent,
        metrics=metrics,
    )

    critic = LLMEvidenceCritic(client=llm_client)

    use_case = InvestigateQuestion(
        planner=orchestrator,
        executor=executor,
        analyst=critic,
    )

    return InvestigationRuntime(
        use_case=use_case,
        metrics=metrics,
    )
