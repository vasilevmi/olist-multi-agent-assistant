"""Сценарий выполнения исследования."""

import logging

from application.investigate.ports import (
    AgentExecutor,
    InvestigationAnalyst,
    InvestigationPlanner,
)
from domain.investigation.entities import Investigation


logger = logging.getLogger(__name__)


class InvestigateQuestion:
    """Последовательно планировать шаги и собирать факты."""

    def __init__(
        self,
        planner: InvestigationPlanner,
        executor: AgentExecutor,
        analyst: InvestigationAnalyst,
        max_steps: int = 10,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps должен быть больше нуля")

        self.planner = planner
        self.executor = executor
        self.analyst = analyst
        self.max_steps = max_steps

    def execute(self, question: str) -> Investigation:
        """Выполнять по одному шагу, пока данных не станет достаточно."""

        investigation = Investigation(question=question)
        investigation.start()
        limitations: list[str] = []

        for _ in range(self.max_steps):
            try:
                decision = self.planner.decide_next_step(
                    question=investigation.question,
                    evidence=investigation.evidence,
                    completed_steps=investigation.steps,
                )
            except Exception as error:
                if investigation.evidence:
                    limitations.append(
                        "Не удалось спланировать дополнительный шаг: "
                        f"{error}"
                    )
                    logger.warning(limitations[-1])
                    break

                investigation.fail(
                    f"Не удалось спланировать следующий шаг: {error}"
                )
                return investigation

            logger.info(
                "Решение оркестратора: complete=%s; reason=%s",
                decision.is_complete,
                decision.reason,
            )

            if decision.is_complete:
                if not investigation.evidence:
                    investigation.fail(
                        "Планировщик завершил исследование без Evidence"
                    )
                    return investigation

                break

            planned_step = decision.next_step

            if planned_step is None:
                investigation.fail(
                    "Планировщик не указал следующий шаг"
                )
                return investigation

            step = investigation.add_step(
                description=planned_step.description,
                agent_name=planned_step.agent_name,
                tool_name=planned_step.tool_name,
                arguments=planned_step.arguments,
            )

            logger.info(
                "Выполняется %s.%s",
                step.agent_name,
                step.tool_name,
            )

            step.start()

            try:
                result = self.executor.execute(
                    agent_name=step.agent_name,
                    task=step.description,
                    tool_name=step.tool_name or "",
                    arguments=step.arguments,
                )
            except Exception as error:
                step.fail(str(error))
                limitations.append(
                    f"Не удалось выполнить шаг «{step.description}»: {error}"
                )
                logger.warning(limitations[-1])
                continue

            step.complete(result)

            investigation.add_evidence(
                source=step.agent_name,
                tool_name=step.tool_name or "unknown",
                data=result,
            )
        else:
            if not investigation.evidence:
                investigation.fail(
                    f"Исследование достигло ограничения в {self.max_steps} шагов"
                )
                return investigation

            limitations.append(
                f"Исследование достигло ограничения в {self.max_steps} шагов"
            )

        try:
            analysis = self.analyst.analyze(
                question=investigation.question,
                evidence=investigation.evidence,
                limitations=limitations,
            )
        except Exception as error:
            investigation.fail(
                f"Не удалось проанализировать данные: {error}"
            )
            return investigation

        for proposed_finding in analysis.findings:
            investigation.add_finding(
                statement=proposed_finding.statement,
                evidence_ids=proposed_finding.evidence_ids,
                confidence=proposed_finding.confidence,
                is_hypothesis=proposed_finding.is_hypothesis,
            )

        investigation.complete(
            final_answer=analysis.final_answer,
            short_summary=analysis.short_summary,
            main_factors=analysis.main_factors,
            conclusion=analysis.conclusion,
            next_checks=analysis.next_checks,
        )

        return investigation
