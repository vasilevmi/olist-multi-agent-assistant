"""Интерфейсы планировщика и исполнителя инструментов."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from domain.investigation.entities import (
    ConfidenceLevel,
    Evidence,
    InvestigationStep,
)


@dataclass
class PlannedStep:
    """Шаг, который предложил планировщик."""

    description: str
    agent_name: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningDecision:
    """Решение оркестратора после проверки уже собранных данных."""

    is_complete: bool
    reason: str
    next_step: PlannedStep | None = None

    def __post_init__(self) -> None:
        if self.is_complete and self.next_step is not None:
            raise ValueError(
                "Завершённое планирование не должно содержать следующий шаг"
            )

        if not self.is_complete and self.next_step is None:
            raise ValueError(
                "Для продолжения исследования нужен следующий шаг"
            )


class InvestigationPlanner(ABC):
    """Интерфейс компонента, выбирающего следующий шаг исследования."""

    @abstractmethod
    def decide_next_step(
        self,
        question: str,
        evidence: list[Evidence],
        completed_steps: list[InvestigationStep],
    ) -> PlanningDecision:
        """Продолжить исследование новым шагом или завершить его."""


class AgentExecutor(ABC):
    """Интерфейс маршрутизатора специализированных агентов."""

    @abstractmethod
    def execute(
        self,
        agent_name: str,
        task: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Передать шаг выбранному агенту и вернуть данные."""


@dataclass
class ProposedFinding:
    """Вывод, предложенный аналитиком."""

    statement: str
    evidence_ids: list[str]
    confidence: ConfidenceLevel
    is_hypothesis: bool = False


@dataclass
class AnalysisResult:
    """Полный результат работы аналитика."""

    findings: list[ProposedFinding]
    final_answer: str
    short_summary: str = ""
    main_factors: list[str] = field(default_factory=list)
    conclusion: str = ""
    next_checks: list[str] = field(default_factory=list)


class InvestigationAnalyst(ABC):
    """Интерфейс компонента, анализирующего собранные факты."""

    @abstractmethod
    def analyze(
        self,
        question: str,
        evidence: list[Evidence],
        limitations: list[str] | None = None,
    ) -> AnalysisResult:
        """Создать выводы с учётом собранных данных и ограничений."""
