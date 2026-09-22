"""Консольный запуск LangChain-исследования."""

import argparse
import asyncio
import json

from infrastructure.bootstrap import create_investigation_runtime


DEFAULT_QUESTION = "Какие категории дают наибольшую выручку?"


def parse_arguments() -> argparse.Namespace:
    """Прочитать вопрос из аргументов командной строки."""

    parser = argparse.ArgumentParser(
        description="Запустить исследование данных Olist.",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION,
        help="Вопрос для мультиагентной системы.",
    )
    return parser.parse_args()


async def run(question: str) -> None:
    """Создать runtime и асинхронно выполнить один вопрос."""

    runtime = await create_investigation_runtime()
    investigation = await runtime.use_case.execute(question=question)
    runtime.metrics.finish()

    print("\nИсследование")
    print(f"ID: {investigation.investigation_id}")
    print(f"Вопрос: {investigation.question}")
    print(f"Статус: {investigation.status.value}")

    print("\nШаги:")
    if not investigation.steps:
        print("- нет выполненных MCP-инструментов")

    for step in investigation.steps:
        print(
            f"- {step.agent_name}.{step.tool_name}: "
            f"{step.status.value}"
        )
        print(f"  Задача: {step.description}")
        if step.error_message is not None:
            print(f"  Ошибка: {step.error_message}")

    print("\nEvidence:")
    if not investigation.evidence:
        print("- Evidence не получены")

    for evidence in investigation.evidence:
        print(
            f"\n[{evidence.evidence_id}] "
            f"{evidence.source}.{evidence.tool_name}"
        )
        print(
            json.dumps(
                evidence.data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    print("\nФакты и гипотезы:")
    if not investigation.findings:
        print("- выводы не сформированы")

    for finding in investigation.findings:
        finding_type = (
            "гипотеза" if finding.is_hypothesis else "факт"
        )
        print(
            f"- [{finding_type}, {finding.confidence.value}] "
            f"{finding.statement}"
        )
        print(f"  Evidence: {', '.join(finding.evidence_ids) or 'нет'}")

    if investigation.short_summary:
        print("\nОтвет:")
        print(investigation.short_summary)

    if investigation.main_factors:
        print("\nОсновные факторы:")
        for factor in investigation.main_factors:
            print(f"- {factor}")

    if investigation.conclusion:
        print("\nТехнический вывод:")
        print(investigation.conclusion)

    if investigation.next_checks:
        print("\nЧто проверить дальше:")
        for check in investigation.next_checks:
            print(f"- {check}")

    if investigation.error_message:
        print(f"\nОшибка: {investigation.error_message}")

    print("\nМетрики:")
    print(f"LLM-вызовов: {runtime.metrics.llm_calls}")
    print(f"Решений Orchestrator: {runtime.metrics.planning_calls}")
    print(f"MCP-инструментов: {runtime.metrics.tool_calls}")
    print(f"Время: {runtime.metrics.duration_seconds:.2f} сек.")


def main() -> None:
    """Синхронная точка входа для запуска async-функции из терминала."""

    arguments = parse_arguments()
    asyncio.run(run(arguments.question))


if __name__ == "__main__":
    main()
