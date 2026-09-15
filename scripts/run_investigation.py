"""Запуск первого исследования продавца."""

import json

from infrastructure.bootstrap import create_investigation_runtime


SELLER_ID = "3504c0cb71d7fa48d967e0e4c94d59d9"


def main() -> None:
    runtime = create_investigation_runtime()

    # Запускаем исследование.
    investigation = runtime.use_case.execute(
        question=(
            f"Проведи анализ продавца {SELLER_ID}"
        )
    )

    runtime.metrics.finish()

    print("\nИсследование")
    print(f"ID: {investigation.investigation_id}")
    print(f"Вопрос: {investigation.question}")
    print(f"Статус: {investigation.status.value}")

    print("\nШаги:")

    for step in investigation.steps:
        print(
            f"- {step.description}: {step.status.value}"
        )

        if step.error_message is not None:
            print(f"  Ошибка: {step.error_message}")

    print("\nПолученные доказательства:")

    for evidence in investigation.evidence:
        print(
            f"\nИсточник: {evidence.source}"
        )
        print(
            f"Инструмент: {evidence.tool_name}"
        )
        print(
            json.dumps(
                evidence.data,
                ensure_ascii=False,
                indent=2,
            )
        )

    print("\nВыводы:")

    for finding in investigation.findings:
        finding_type = (
            "гипотеза" if finding.is_hypothesis else "факт"
        )
        print(
            f"- [{finding_type}, {finding.confidence.value}] "
            f"{finding.statement}"
        )

    if investigation.final_answer is not None:
        print("\nИтоговый ответ:")
        print(investigation.final_answer)

    if investigation.error_message is not None:
        print(
            f"\nОшибка исследования: "
            f"{investigation.error_message}"
        )

    print("\nМетрики выполнения:")
    print(f"LLM-вызовов: {runtime.metrics.llm_calls}")
    print(f"Решений оркестратора: {runtime.metrics.planning_calls}")
    print(f"Выполненных инструментов: {runtime.metrics.tool_calls}")
    print(f"Время: {runtime.metrics.duration_seconds:.2f} сек.")


if __name__ == "__main__":
    main()
