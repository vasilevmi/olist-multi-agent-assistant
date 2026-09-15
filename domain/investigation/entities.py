"""Сущности процесса исследования бизнес-вопроса."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class InvestigationStatus(str, Enum):
    """Состояние всего исследования."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Состояние одного шага плана."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    """Уверенность в сформулированном выводе."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class InvestigationStep:
    """Одна операция в плане исследования."""

    description: str
    agent_name: str
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    step_id: str = field(default_factory=lambda: str(uuid4()))
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None
    error_message: str | None = None

    def start(self) -> None:
        """Перевести шаг в состояние выполнения."""
        self.status = StepStatus.IN_PROGRESS
        self.error_message = None

    def complete(self, result: dict[str, Any]) -> None:
        """Сохранить результат и завершить шаг."""
        self.result = result
        self.status = StepStatus.COMPLETED
        self.error_message = None

    def fail(self, error_message: str) -> None:
        """Отметить неудачное выполнение шага."""
        self.status = StepStatus.FAILED
        self.error_message = error_message


@dataclass
class Evidence:
    """Факт, полученный от конкретного MCP-инструмента."""

    source: str
    tool_name: str
    data: dict[str, Any]
    evidence_id: str = field(default_factory=lambda: str(uuid4()))
    collected_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )


@dataclass
class Finding:
    """Вывод, основанный на одном или нескольких доказательствах."""

    statement: str
    evidence_ids: list[str]
    confidence: ConfidenceLevel
    is_hypothesis: bool = False
    finding_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Investigation:
    """Полное исследование одного вопроса пользователя."""

    question: str
    investigation_id: str = field(default_factory=lambda: str(uuid4()))
    status: InvestigationStatus = InvestigationStatus.CREATED
    steps: list[InvestigationStep] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    final_answer: str | None = None
    short_summary: str | None = None
    main_factors: list[str] = field(default_factory=list)
    conclusion: str | None = None
    next_checks: list[str] = field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("Вопрос исследования не должен быть пустым")

    def add_step(
        self,
        description: str,
        agent_name: str,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> InvestigationStep:
        """Добавить новый шаг в план исследования."""

        step = InvestigationStep(
            description=description,
            agent_name=agent_name,
            tool_name=tool_name,
            arguments=arguments or {},
        )

        self.steps.append(step)

        return step

    def start(self) -> None:
        """Начать выполнение исследования."""
        self.status = InvestigationStatus.IN_PROGRESS
        self.error_message = None

    def add_evidence(
        self,
        source: str,
        tool_name: str,
        data: dict[str, Any],
    ) -> Evidence:
        """Добавить проверяемый факт, полученный через инструмент."""
        evidence = Evidence(
            source=source,
            tool_name=tool_name,
            data=data,
        )
        self.evidence.append(evidence)
        return evidence

    def add_finding(
        self,
        statement: str,
        evidence_ids: list[str],
        confidence: ConfidenceLevel,
        is_hypothesis: bool = False,
    ) -> Finding:
        """Добавить вывод и связать его с доказательствами."""
        known_evidence_ids = {
            item.evidence_id for item in self.evidence
        }
        unknown_ids = set(evidence_ids) - known_evidence_ids
        if unknown_ids:
            raise ValueError(
                "Вывод ссылается на неизвестные evidence_id: "
                + ", ".join(sorted(unknown_ids))
            )

        finding = Finding(
            statement=statement,
            evidence_ids=evidence_ids,
            confidence=confidence,
            is_hypothesis=is_hypothesis,
        )
        self.findings.append(finding)
        return finding

    def complete(
        self,
        final_answer: str,
        short_summary: str | None = None,
        main_factors: list[str] | None = None,
        conclusion: str | None = None,
        next_checks: list[str] | None = None,
    ) -> None:
        """Сохранить итоговый ответ и завершить исследование."""
        final_answer = final_answer.strip()
        if not final_answer:
            raise ValueError("Финальный ответ не должен быть пустым")
        self.final_answer = final_answer
        self.short_summary = short_summary
        self.main_factors = main_factors or []
        self.conclusion = conclusion
        self.next_checks = next_checks or []
        self.status = InvestigationStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.error_message = None

    def fail(self, error_message: str) -> None:
        """Завершить исследование с ошибкой."""
        self.status = InvestigationStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now(UTC)
