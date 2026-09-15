# Evaluation

Контрольный набор содержит 25 бизнес-кейсов:

- 16 детерминированных кейсов с заранее рассчитанными SQL-ответами;
- 9 исследовательских кейсов, для которых проверяются выбранные инструменты,
  полнота Evidence, привязка выводов к Evidence и структура ответа.

## Запуск

Показать список кейсов без обращения к LLM:

```powershell
py -m evaluation.run_evaluation --list
```

Запустить один кейс:

```powershell
py -m evaluation.run_evaluation --case-id D007
```

Запустить несколько конкретных кейсов:

```powershell
py -m evaluation.run_evaluation --case-id D006 --case-id D007
```

Запустить только детерминированные кейсы:

```powershell
py -m evaluation.run_evaluation --type deterministic
```

Полный запуск:

```powershell
py -m evaluation.run_evaluation
```

Отчёты сохраняются в `evaluation/reports/`. Полный прогон выполняет много
LLM-запросов, поэтому перед запуском проверьте лимиты выбранного провайдера.
Для экономии запросов кейсы можно запускать по одному или небольшими группами.

## Метрики

Подробная памятка простым языком: [METRICS.md](METRICS.md).

- `case_success_rate` — доля полностью успешных кейсов;
- `factual_accuracy` — доля совпавших детерминированных проверок;
- `average_evidence_coverage` — покрытие обязательных источников Evidence;
- `tool_selection_error_rate` — доля кейсов с ошибочным выбором инструментов;
- `evidence_grounding_rate` — доля ответов с корректными ссылками на Evidence;
- `structured_answer_rate` — доля ответов со всеми обязательными блоками;
- `average_tool_calls`, `average_llm_calls`, `average_latency_seconds`.

Кейсы D001, D003, D004 и часть D005 описывают обязательные возможности ТЗ,
которые следует реализовать, даже если соответствующего инструмента пока нет.
Evaluation должен показывать такие пробелы как ошибки, а не скрывать их.
