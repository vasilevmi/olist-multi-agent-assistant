"""Оркестратор исследования пользовательского вопроса."""

import json
import re
from typing import Any

from application.investigate.ports import (
    InvestigationPlanner,
    PlanningDecision,
    PlannedStep,
)
from domain.investigation.entities import Evidence, InvestigationStep
from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)
from infrastructure.observability.run_metrics import RunMetrics


class LLMOrchestrator(InvestigationPlanner):
    """Разбивает вопрос на шаги и выбирает нужных агентов."""

    AVAILABLE_TOOLS = {
        "sales_agent": {
            "get_sales_summary": (
                "Общие показатели продаж магазина за всё время. "
                "Аргументы не требуются."
            ),
            "get_order_by_id": (
                "Получить заказ и все его товарные позиции. Обязательный "
                "аргумент: order_id. Результат содержит product_id и "
                "seller_id каждой позиции. Используй этот инструмент, если "
                "из Evidence известен order_id и нужно узнать состав заказа."
            ),
            "get_sales_by_period": (
                "Показатели продаж магазина за период. "
                "Аргументы: start_date и end_date в формате YYYY-MM-DD."
            ),
            "get_sales_by_category": (
                "Продажи конкретной категории. Обязательный аргумент: "
                "category_name. Необязательные: start_date, end_date."
            ),
            "get_category_sales_ranking": (
                "Получить рейтинг всех товарных категорий по продажам. "
                "Необязательные аргументы: limit, ranking_metric "
                "(total_revenue, total_orders или total_items), start_date, "
                "end_date. Для вопроса о категориях с наибольшей выручкой "
                "используй total_revenue."
            ),
            "get_seller_sales": (
                "Получить количество заказов, выручку и средний чек "
                "конкретного продавца. Обязательный аргумент: seller_id. "
                "Необязательные: start_date, end_date."
            ),
            "get_top_sellers": (
                "Получить топ продавцов по выручке. Необязательные "
                "аргументы: limit, start_date, end_date."
            ),
            "compare_sellers": (
                "Сравнить нескольких продавцов. Обязательный аргумент: "
                "seller_ids — список идентификаторов. Необязательные: "
                "start_date, end_date."
            ),
            "get_product": (
                "Получить карточку товара. Аргумент: product_id."
            ),
            "get_category": (
                "Получить информацию о категории и количестве товаров. "
                "Аргумент: category_name."
            ),
            "get_category_products": (
                "Получить товары категории. Обязательный аргумент: "
                "category_name. Необязательный: limit."
            ),
            "get_product_statistics": (
                "Получить продажи конкретного товара. Обязательный "
                "аргумент: product_id. Необязательные: start_date, "
                "end_date."
            ),
        },
        "seller_agent": {
            "get_seller": (
                "Получить город, штат и основную информацию о продавце. "
                "Аргумент: seller_id."
            ),
            "get_sellers_by_location": (
                "Найти продавцов по местоположению. Необязательные "
                "аргументы: state, city, limit. Нужно указать state "
                "или city."
            ),
            "get_seller_catalog": (
                "Получить категории и уникальные товары продавца. "
                "Обязательный аргумент: seller_id. Необязательный: "
                "product_limit."
            ),
            "get_seller_top_products": (
                "Получить самые продаваемые товары продавца по выручке. "
                "Обязательный аргумент: seller_id. Необязательный: limit."
            ),
            "find_high_sales_low_rating_sellers": (
                "Найти продавцов с высокой выручкой и низким рейтингом. "
                "Высокие продажи означают верхнюю выборку продавцов по "
                "выручке, а низкий рейтинг — ниже среднего рейтинга магазина "
                "или ниже аргумента max_rating. Необязательные аргументы: "
                "candidate_limit, result_limit, max_rating. Инструмент сразу "
                "проверяет рейтинги всей верхней выборки."
            ),
        },
        "delivery_agent": {
            "get_delivery_by_order_id": (
                "Получить даты и состояние доставки одного заказа. "
                "Аргумент: order_id."
            ),
            "get_delivery_statistics": (
                "Получить общую статистику доставки магазина. "
                "Необязательные аргументы: start_date, end_date."
            ),
            "get_delayed_orders": (
                "Получить самые сильно задержанные заказы магазина. "
                "Необязательные аргументы: limit, start_date, end_date."
            ),
            "get_seller_delivery_performance": (
                "Получить сроки доставки и процент задержек "
                "конкретного продавца. Обязательный аргумент: seller_id. "
                "Необязательные: start_date, end_date."
            ),
            "find_sellers_by_delay_rate": (
                "Найти всех продавцов, у которых доля задержанных заказов "
                "строго выше заданного порога. Необязательные аргументы: "
                "delay_threshold — доля от 0 до 1 (для 20% передай 0.20), "
                "min_orders, start_date, end_date. Для вопроса о продавцах "
                "выше порога используй этот инструмент."
            ),
            "get_seller_average_delivery_time": (
                "Получить среднее время доставки продавца. Обязательный "
                "аргумент: seller_id. Необязательные: start_date, "
                "end_date."
            ),
            "get_delivery_by_region": (
                "Получить показатели доставки в штате покупателей. "
                "Обязательный аргумент: region. Необязательные: "
                "start_date, end_date."
            ),
            "get_category_delivery_ranking": (
                "Получить рейтинг товарных категорий по задержкам доставки. "
                "Необязательные аргументы: limit, min_orders, ranking_metric "
                "(delayed_share или delayed_orders), start_date, end_date. "
                "Для вопроса, какие категории больше всего страдают от "
                "задержек, используй delayed_share; по умолчанию учитываются "
                "категории минимум со 100 доставленными заказами."
            ),
            "get_region_delivery_ranking": (
                "Получить рейтинг регионов покупателей по доставке. "
                "Необязательные аргументы: limit, min_orders, ranking_metric "
                "(delayed_share, delayed_orders или average_delivery_days), "
                "start_date, end_date. Для вопроса, где чаще нарушается "
                "ожидаемый срок, используй delayed_share; для вопроса, где "
                "среднее время доставки самое большое, обязательно используй "
                "average_delivery_days."
            ),
        },
        "reviews_agent": {
            "analyze_delivery_rating_relationship": (
                "Сравнить оценки задержанных и своевременно доставленных "
                "заказов и рассчитать корреляцию оценки с фактом и "
                "продолжительностью задержки. Необязательные аргументы: "
                "seller_id, start_date, end_date. Если вопрос относится к "
                "конкретному продавцу, обязательно передай seller_id; без "
                "него анализ выполняется по всему магазину."
            ),
            "get_review_statistics": (
                "Получить общую статистику отзывов магазина. "
                "Необязательные аргументы: start_date, end_date."
            ),
            "get_seller_rating": (
                "Получить среднюю оценку и статистику отзывов "
                "конкретного продавца. Обязательный аргумент: seller_id. "
                "Возвращает также точное распределение оценок 1–5. "
                "Необязательные: start_date, end_date."
            ),
            "get_category_rating": (
                "Получить рейтинг заказов выбранной категории. "
                "Обязательный аргумент: category_name. Необязательные: "
                "start_date, end_date."
            ),
            "get_category_rating_ranking": (
                "Получить рейтинг всех категорий по средней оценке. "
                "Необязательные аргументы: limit, min_reviews, start_date, "
                "end_date. Для вопроса о категории с самым высоким средним "
                "рейтингом используй этот инструмент; min_reviews задаёт "
                "минимально допустимое число отзывов."
            ),
            "get_category_negative_review_ranking": (
                "Получить рейтинг всех категорий по доле негативных отзывов "
                "с оценкой 1 или 2. Необязательные аргументы: limit, "
                "min_reviews, start_date, end_date. Для вопроса о категории "
                "с наибольшей долей плохих отзывов используй этот инструмент."
            ),
            "get_product_review_summary": (
                "Получить сводку отзывов о конкретном товаре. "
                "Обязательный аргумент: product_id. Необязательные: "
                "start_date, end_date."
            ),
            "get_negative_reviews": (
                "Получить последние негативные отзывы по всему магазину. "
                "Не поддерживает seller_id, product_id или category_name. "
                "Необязательные аргументы: limit, start_date, end_date."
            ),
            "get_seller_negative_reviews": (
                "Получить последние негативные отзывы заказов конкретного "
                "продавца для поиска повторяющихся жалоб. Обязательный "
                "аргумент: seller_id. Необязательные: limit (максимум 50), "
                "start_date, end_date. Результат является ограниченной "
                "выборкой, а отзыв относится ко всему заказу."
            ),
            "get_rating_distribution": (
                "Получить распределение оценок от 1 до 5 по магазину. "
                "Необязательные аргументы: start_date, end_date."
            ),
        },
    }

    def __init__(
        self,
        client: OpenAICompatibleClient,
        metrics: RunMetrics | None = None,
    ) -> None:
        self.client = client
        self.metrics = metrics

    def decide_next_step(
        self,
        question: str,
        evidence: list[Evidence],
        completed_steps: list[InvestigationStep],
    ) -> PlanningDecision:
        """Выбрать один следующий шаг или завершить исследование."""

        tools_json = json.dumps(
            self.AVAILABLE_TOOLS,
            ensure_ascii=False,
            indent=2,
        )

        completed_steps_data = [
            {
                "description": step.description,
                "agent_name": step.agent_name,
                "tool_name": step.tool_name,
                "arguments": step.arguments,
                "status": step.status.value,
                "error_message": step.error_message,
            }
            for step in completed_steps
        ]

        evidence_data = [
            {
                "source": item.source,
                "tool_name": item.tool_name,
                "data": item.data,
            }
            for item in evidence
        ]

        system_prompt = f"""
Ты orchestrator системы анализа интернет-магазина Olist.

Твоя задача:
1. Понять вопрос пользователя.
2. Изучить результаты уже выполненных шагов.
3. Решить, достаточно ли данных для ответа.
4. Если данных недостаточно, выбрать ровно один следующий инструмент.

Доступные агенты и инструменты:

{tools_json}

Правила:
- используй только перечисленные агенты и инструменты;
- не придумывай seller_id, product_id, order_id, категории, регионы и даты;
- идентификаторы и фильтры бери только из вопроса или Evidence;
- не передавай аргументы, которых нет в описании инструмента;
- не вызывай агента, если его данные не нужны;
- не повторяй уже выполненный инструмент с теми же аргументами;
- учитывай status и error_message предыдущих шагов; после failed выбери
  другой подход или заверши исследование с уже собранными Evidence;
- возвращай не весь план, а только один следующий шаг;
- выбирай инструмент, который возвращает все запрошенные в шаге показатели;
- не описывай в шаге показатели, которых выбранный инструмент не возвращает;
- самостоятельно определяй необходимые аспекты анализа по вопросу;
- заранее заданного количества шагов нет;
- заверши исследование, когда Evidence уже позволяют ответить на вопрос;
- не завершай исследование, если для существенного вывода не хватает фактов;
- для вопроса о продавцах с высокими продажами и низким рейтингом используй
  find_high_sales_low_rating_sellers вместо проверки одного продавца;
- слова «все», «только» и «единственный» допустимы лишь после проверки всей
  явно определённой выборки;
- понятия «высокий» и «низкий» должны иметь порог или сравнение в Evidence;
- get_seller_average_delivery_time возвращает только среднее время доставки;
  для процента и количества задержек используй
  get_seller_delivery_performance;
- get_seller_delivery_performance уже возвращает среднее время доставки;
  не используй его одновременно с get_seller_average_delivery_time;
- для поиска всех продавцов с долей задержек выше заданного порога
  используй find_sellers_by_delay_rate, а не проверяй продавцов по одному;
- для сравнения задержек между товарными категориями используй
  get_category_delivery_ranking, а не get_delayed_orders;
- для сравнения задержек между всеми регионами используй
  get_region_delivery_ranking, а не многократные вызовы
  get_delivery_by_region;
- для вопроса о связи задержки доставки с оценкой клиента используй
  analyze_delivery_rating_relationship: этот инструмент уже объединяет
  доставки и отзывы, поэтому отдельные общие сводки не нужны; для вопроса
  о конкретном продавце обязательно передавай его seller_id;
- для сравнения продаж всех категорий используй
  get_category_sales_ranking, а не многократные вызовы
  get_sales_by_category;
- для сравнения среднего рейтинга всех категорий используй
  get_category_rating_ranking, а не многократные вызовы
  get_category_rating;
- для сравнения доли плохих отзывов между всеми категориями используй
  get_category_negative_review_ranking; плохими считаются оценки 1 и 2;
- если пользователь явно перечислил аспекты сложного анализа продавца,
  не завершай исследование, пока Evidence не покрывают каждый из них:
  продажи и структуру ассортимента, доставку, распределение отзывов,
  сравнение со средними показателями и связь задержек с оценками;
- для структуры ассортимента продавца используй get_seller_catalog,
  для количества заказов и выручки — get_seller_sales;
- отзыв содержит order_id, а не product_id; чтобы определить товары из
  заказа отзыва, сначала используй get_order_by_id с этим order_id;
- не передавай order_id в get_product: get_product принимает только product_id;
- для сравнения продавца со средними значениями магазина используй
  соответствующую сводку продавца и общую сводку того же показателя;
- чтобы объяснить, почему рейтинг продавца ниже среднего, сравни
  get_seller_rating с get_review_statistics и изучи ограниченную выборку
  get_seller_negative_reviews; не используй для этого общий
  get_negative_reviews;
- если пользователь просит только рейтинг и общую статистику отзывов
  конкретного продавца, используй get_seller_rating и не исследуй тексты
  негативных отзывов или состав заказов без отдельной просьбы;
- при action=continue поле next_step должно содержать один шаг;
- при action=finish поле next_step должно быть null;
- arguments всегда должен быть JSON-объектом;
- верни только JSON без дополнительного текста.

Формат продолжения:

{{
  "action": "continue",
  "reason": "Каких данных пока не хватает",
  "next_step": {{
    "description": "Описание одного шага",
    "agent_name": "sales_agent",
    "tool_name": "get_seller_sales",
    "arguments": {{
      "seller_id": "идентификатор из вопроса или Evidence"
    }}
  }}
}}

Формат завершения:

{{
  "action": "finish",
  "reason": "Почему собранных данных достаточно",
  "next_step": null
}}
""".strip()

        user_prompt = json.dumps(
            {
                "question": question,
                "completed_steps": completed_steps_data,
                "evidence": evidence_data,
            },
            ensure_ascii=False,
            indent=2,
        )

        if self.metrics is not None:
            self.metrics.record_planning_call()

        response = self.client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1000,
        )

        return self._create_decision(
            response=response,
            question=question,
            completed_steps=completed_steps,
        )

    def _create_decision(
        self,
        response: dict[str, Any],
        question: str,
        completed_steps: list[InvestigationStep],
    ) -> PlanningDecision:
        """Проверить решение, которое вернула модель."""

        action = response.get("action")
        reason = response.get("reason")

        if action not in {"continue", "finish"}:
            raise ValueError(
                "action должен быть continue или finish"
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "Orchestrator не объяснил причину решения"
            )

        if action == "finish":
            missing_step = self._get_missing_explicit_step(
                question=question,
                completed_steps=completed_steps,
            )
            if missing_step is not None:
                return PlanningDecision(
                    is_complete=False,
                    reason=(
                        "Нельзя завершить исследование: не проверен явно "
                        f"запрошенный аспект — {missing_step.description}"
                    ),
                    next_step=missing_step,
                )
            return PlanningDecision(
                is_complete=True,
                reason=reason.strip(),
            )

        planned_step = self._create_planned_step(
            response.get("next_step")
        )

        for completed_step in completed_steps:
            if (
                completed_step.agent_name == planned_step.agent_name
                and completed_step.tool_name == planned_step.tool_name
                and completed_step.arguments == planned_step.arguments
            ):
                raise ValueError(
                    "Orchestrator повторил уже выполненный шаг"
                )

        return PlanningDecision(
            is_complete=False,
            reason=reason.strip(),
            next_step=planned_step,
        )

    @staticmethod
    def _get_missing_explicit_step(
        question: str,
        completed_steps: list[InvestigationStep],
    ) -> PlannedStep | None:
        """Не позволить LLM пропустить явно запрошенную часть анализа."""

        normalized_question = question.lower()
        seller_match = re.search(r"\b[0-9a-f]{32}\b", normalized_question)
        if seller_match is None:
            return None

        seller_id = seller_match.group(0)
        completed_tools = {
            step.tool_name
            for step in completed_steps
            if step.status.value == "completed"
        }
        requirements: list[tuple[bool, PlannedStep]] = [
            (
                "структур" in normalized_question,
                PlannedStep(
                    description="Получить показатели заказов продавца",
                    agent_name="sales_agent",
                    tool_name="get_seller_sales",
                    arguments={"seller_id": seller_id},
                ),
            ),
            (
                "структур" in normalized_question,
                PlannedStep(
                    description="Получить категории и ассортимент продавца",
                    agent_name="seller_agent",
                    tool_name="get_seller_catalog",
                    arguments={"seller_id": seller_id},
                ),
            ),
            (
                (
                    "срок" in normalized_question
                    or "доля задерж" in normalized_question
                ),
                PlannedStep(
                    description="Проверить доставку и задержки продавца",
                    agent_name="delivery_agent",
                    tool_name="get_seller_delivery_performance",
                    arguments={"seller_id": seller_id},
                ),
            ),
            (
                "распределен" in normalized_question,
                PlannedStep(
                    description="Получить распределение оценок продавца",
                    agent_name="reviews_agent",
                    tool_name="get_seller_rating",
                    arguments={"seller_id": seller_id},
                ),
            ),
            (
                "средн" in normalized_question,
                PlannedStep(
                    description="Получить средние показатели отзывов магазина",
                    agent_name="reviews_agent",
                    tool_name="get_review_statistics",
                    arguments={},
                ),
            ),
            (
                (
                    "связ" in normalized_question
                    and "задерж" in normalized_question
                ),
                PlannedStep(
                    description=(
                        "Проверить связь задержек с оценками продавца"
                    ),
                    agent_name="reviews_agent",
                    tool_name="analyze_delivery_rating_relationship",
                    arguments={"seller_id": seller_id},
                ),
            ),
            (
                (
                    "почему" in normalized_question
                    and "рейтинг" in normalized_question
                ),
                PlannedStep(
                    description="Изучить негативные отзывы продавца",
                    agent_name="reviews_agent",
                    tool_name="get_seller_negative_reviews",
                    arguments={"seller_id": seller_id, "limit": 20},
                ),
            ),
        ]

        for is_required, step in requirements:
            if is_required and step.tool_name not in completed_tools:
                return step

        return None

    def _create_planned_step(
        self,
        raw_step: Any,
    ) -> PlannedStep:
        """Проверить ответ LLM и создать один шаг плана."""

        # Некоторые модели помещают JSON-объект шага внутрь строки.
        # Превращаем такую строку обратно в обычный словарь Python.
        if isinstance(raw_step, str):
            try:
                raw_step = json.loads(raw_step)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Строка шага содержит некорректный JSON"
                ) from error

        if not isinstance(raw_step, dict):
            raise ValueError(
                "Каждый шаг должен быть JSON-объектом"
            )

        description = raw_step.get("description")
        agent_name = raw_step.get("agent_name")
        tool_name = raw_step.get("tool_name")
        arguments = raw_step.get("arguments")

        if not isinstance(description, str):
            raise ValueError(
                "У шага отсутствует description"
            )

        if agent_name not in self.AVAILABLE_TOOLS:
            raise ValueError(
                f"Неизвестный агент: {agent_name}"
            )

        allowed_tools = self.AVAILABLE_TOOLS[agent_name]

        if tool_name not in allowed_tools:
            raise ValueError(
                f"Агенту {agent_name} недоступен "
                f"инструмент {tool_name}"
            )

        if not isinstance(arguments, dict):
            raise ValueError(
                "arguments должен быть JSON-объектом"
            )

        return PlannedStep(
            description=description,
            agent_name=agent_name,
            tool_name=tool_name,
            arguments=arguments,
        )
