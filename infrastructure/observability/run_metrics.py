"""Метрики одного запуска исследования."""

from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class RunMetrics:
    """Считает LLM-вызовы, инструменты и время выполнения."""

    llm_calls: int = 0
    planning_calls: int = 0
    tool_calls: int = 0
    _started_at: float = field(
        default_factory=perf_counter,
        repr=False,
    )
    _finished_at: float | None = field(
        default=None,
        repr=False,
    )

    def record_llm_call(self) -> None:
        """Учесть один логический запрос к языковой модели."""
        self.llm_calls += 1

    def record_planning_call(self) -> None:
        """Учесть одно решение оркестратора."""
        self.planning_calls += 1

    def record_tool_call(self) -> None:
        """Учесть один успешно выполненный доменный инструмент."""
        self.tool_calls += 1

    def finish(self) -> None:
        """Зафиксировать время окончания исследования."""
        if self._finished_at is None:
            self._finished_at = perf_counter()

    @property
    def duration_seconds(self) -> float:
        """Вернуть длительность запуска в секундах."""
        end_time = self._finished_at or perf_counter()
        return end_time - self._started_at
