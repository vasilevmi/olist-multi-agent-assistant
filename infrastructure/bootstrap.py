"""Сборка LangChain-компонентов приложения в единый runtime."""

from dataclasses import dataclass

from application.investigate.use_cases import InvestigateQuestion
from infrastructure.agents.evidence_critic import create_evidence_critic
from infrastructure.agents.orchestrator import create_orchestrator
from infrastructure.llm.langchain_client import create_chat_model
from infrastructure.observability.langfuse_tracing import (
    create_langfuse_handler,
)
from infrastructure.observability.run_metrics import RunMetrics
from infrastructure.observability.traced_investigation import (
    TracedInvestigateQuestion,
)


@dataclass
class InvestigationRuntime:
    """Готовый сценарий исследования и метрики одного запуска."""

    use_case: TracedInvestigateQuestion
    metrics: RunMetrics


async def create_investigation_runtime() -> InvestigationRuntime:
    """Создать LangChain-агентов и объединить их в рабочий сценарий."""

    metrics = RunMetrics()
    model = create_chat_model()

    orchestrator = await create_orchestrator(model)
    critic = create_evidence_critic(model)

    investigation = InvestigateQuestion(
        orchestrator=orchestrator,
        critic=critic,
    )

    traced_investigation = TracedInvestigateQuestion(
        use_case=investigation,
        langfuse_handler=create_langfuse_handler(),
    )

    return InvestigationRuntime(
        use_case=traced_investigation,
        metrics=metrics,
    )
