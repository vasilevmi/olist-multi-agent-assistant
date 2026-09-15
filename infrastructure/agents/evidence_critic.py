"""LLM-агент проверки доказательств и выводов."""

import json
from typing import Any

from application.investigate.ports import (
    AnalysisResult,
    InvestigationAnalyst,
    ProposedFinding,
)
from domain.investigation.entities import (
    ConfidenceLevel,
    Evidence,
)
from infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleClient,
)


class LLMEvidenceCritic(InvestigationAnalyst):
    """Проверяет Evidence и формирует подтверждённые выводы."""

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def analyze(
        self,
        question: str,
        evidence: list[Evidence],
        limitations: list[str] | None = None,
    ) -> AnalysisResult:
        """Проверить факты и сформировать итоговый ответ."""

        if not evidence:
            raise ValueError(
                "Critic не получил Evidence для анализа"
            )

        evidence_data = [
            {
                "evidence_id": item.evidence_id,
                "source": item.source,
                "tool_name": item.tool_name,
                "data": item.data,
            }
            for item in evidence
        ]

        response = self.client.generate_json(
            system_prompt=(
                "Ты Critic / Evidence Agent системы Olist. "
                "Если вопрос задан на русском языке, все statement и поля "
                "ответа обязательно пиши только на русском языке. "
                "Проверяй выводы только по предоставленным Evidence. "
                "Не придумывай числа и факты. "
                "Не добавляй обозначение валюты, если оно явно не указано "
                "в Evidence. "
                "Если в Evidence currency=BRL, оформляй денежные значения "
                "как R$ с пробелами между разрядами и двумя знаками после "
                "запятой. "
                "Для рейтинговых выборок обязательно указывай их границы: "
                "размер пула кандидатов, метрику ранжирования и порог. "
                "Для рейтинга задержек категорий перечисли минимум первые "
                "три категории и для каждой укажи delayed_percentage, "
                "delayed_orders и total_delivered_orders. Также назови "
                "ranking_metric и фильтр min_orders из Evidence. "
                "Для рейтинга регионов перечисли минимум первые три региона. "
                "Если ranking_metric=average_delivery_days, укажи для каждого "
                "average_delivery_days и total_delivered_orders; иначе укажи "
                "delayed_percentage, delayed_orders и total_delivered_orders. "
                "Всегда назови ranking_metric и фильтр min_orders. "
                "Для analyze_delivery_rating_relationship сравни обе группы "
                "по средней оценке и доле негативных отзывов, укажи обе "
                "корреляции, явно назови analysis_scope и не называй "
                "статистическую связь доказанной причиной. "
                "Для get_category_sales_ranking перечисли минимум первые "
                "три категории, их total_revenue и total_orders, назови "
                "ranking_metric и определение выручки из Evidence. "
                "Для get_category_negative_review_ranking назови минимум "
                "первые три категории, их negative_percentage, "
                "negative_reviews и total_reviews, а также min_reviews и "
                "определение негативного отзыва из Evidence. "
                "Для find_sellers_by_delay_rate сформируй один общий finding, "
                "укажи число найденных продавцов, порог и min_orders. "
                "Идентификаторы продавцов перечисляй компактно через запятую, "
                "не создавай отдельный finding и отдельное описание для "
                "каждого продавца. Для этого инструмента верни не более трёх "
                "main_factors и не более двух next_checks. "
                "Не используй слова только, единственный или все, если "
                "Evidence не подтверждает проверку всей указанной выборки. "
                "Не делай вывод о текущей активности продавца только "
                "на основании исторических заказов. "
                "Технические названия городов, штатов и категорий сохраняй "
                "так, как они записаны в Evidence. В тексте для пользователя "
                "можешь добавить понятный русский перевод категории, но "
                "исходное техническое имя обязательно оставь в скобках. "
                "Используй смысл полей буквально и не переименовывай "
                "технические поля в новые бизнес-показатели. "
                "Поле listed_products означает количество товаров, "
                "перечисленных в ответе инструмента, а не возвраты. "
                "Если есть Evidence от get_seller_negative_reviews, "
                "обязательно выдели конкретные повторяющиеся темы жалоб из "
                "comment_title и comment_message, укажи число изученных "
                "отзывов и размер запрошенной выборки. Отзывы без текста не "
                "используй для определения темы. Такие объяснения оформляй "
                "как гипотезы или возможные факторы, а не доказанные причины. "
                "Учитывай attribution_scope: отзыв относится ко всему заказу "
                "и не всегда однозначно к выбранному продавцу. "
                "В доступных данных нет информации о возвратах и refund. "
                "Список лучших товаров может быть ограничен параметром "
                "limit и не доказывает полную выручку категории. "
                "Каждый фактический вывод обязан содержать "
                "evidence_ids существующих доказательств. "
                "Если причинная связь не доказана, обозначь её "
                "как гипотезу и установи is_hypothesis=true. "
                "Причинная гипотеза без прямого сравнения должна иметь "
                "confidence=low. "
                "Confidence=high используй только для значений, которые "
                "прямо присутствуют в Evidence. "
                "Confidence=medium используй для простых выводов, "
                "полученных сравнением нескольких Evidence. "
                "Если данных недостаточно, прямо укажи ограничение. "
                "Если передан список limitations, не считай его Evidence и "
                "не извлекай из него бизнес-факты. Используй его только для "
                "честного объяснения того, какую часть вопроса проверить не "
                "удалось. Всё равно сформируй максимально полезный ответ по "
                "уже полученным Evidence. "
                "Уровень confidence может быть только "
                "low, medium или high. "
                "Каждый элемент main_factors должен быть полноценным "
                "понятным бизнес-фактом с конкретным значением из Evidence. "
                "Не помещай туда одиночные технические имена полей вроде "
                "total_revenue. В next_checks записывай конкретные действия, "
                "которые помогут проверить оставшиеся гипотезы или ограничения. "
                "Пиши кратко и не повторяй одно утверждение в нескольких "
                "разделах. short_summary является основным ответом, который "
                "увидит пользователь. Сделай его самостоятельным связным "
                "абзацем из 3–5 предложений: сразу ответь на вопрос, приведи "
                "главные подтверждённые значения и факторы, а при нехватке "
                "данных честно назови ограничение. short_summary должен быть "
                "понятен без чтения main_factors и conclusion. "
                "Отвечай именно на формулировку вопроса пользователя, не "
                "подменяй её общим описанием полученных данных. Если данные "
                "исторические или ограничены периодом/выборкой, кратко укажи "
                "это и не представляй результат как текущий. "
                "main_factors используй как структурированные факты для "
                "технических деталей, а conclusion — для интерпретации и "
                "границ расчёта, не копируя список факторов. Техническое имя "
                "MCP-инструмента и ключевые технические поля оставляй в "
                "conclusion — они нужны для аудита. "
                "Верни только JSON следующего формата: "
                "{"
                '"findings": ['
                "{"
                '"statement": "вывод", '
                '"evidence_ids": ["id"], '
                '"confidence": "high", '
                '"is_hypothesis": false'
                "}"
                "], "
                '"short_summary": "краткий вывод", '
                '"main_factors": ["фактор 1", "фактор 2"], '
                '"conclusion": "вывод только по Evidence", '
                '"next_checks": ["что полезно проверить дальше"]'
                "}."
            ),
            user_prompt=json.dumps(
                {
                    "question": question,
                    "evidence": evidence_data,
                    "limitations": limitations or [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            max_tokens=1800,
            json_schema={
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "statement": {"type": "string"},
                                "evidence_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"],
                                },
                                "is_hypothesis": {"type": "boolean"},
                            },
                            "required": [
                                "statement",
                                "evidence_ids",
                                "confidence",
                                "is_hypothesis",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "short_summary": {"type": "string"},
                    "main_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "conclusion": {"type": "string"},
                    "next_checks": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "findings",
                    "short_summary",
                    "main_factors",
                    "conclusion",
                    "next_checks",
                ],
                "additionalProperties": False,
            },
        )

        raw_findings = response.get("findings")
        short_summary = response.get("short_summary")
        main_factors = response.get("main_factors")
        conclusion = response.get("conclusion")
        next_checks = response.get("next_checks")

        if not isinstance(raw_findings, list):
            raise ValueError(
                "Critic не вернул список findings"
            )

        if not isinstance(short_summary, str) or not short_summary.strip():
            raise ValueError(
                "Critic не вернул краткий вывод"
            )

        if not isinstance(conclusion, str) or not conclusion.strip():
            raise ValueError(
                "Critic не вернул итоговый вывод"
            )

        if not isinstance(main_factors, list) or not all(
            isinstance(item, str) and item.strip()
            for item in main_factors
        ):
            raise ValueError("Critic вернул некорректные основные факторы")

        if not isinstance(next_checks, list) or not all(
            isinstance(item, str) and item.strip()
            for item in next_checks
        ):
            raise ValueError("Critic вернул некорректные дальнейшие проверки")

        short_summary = short_summary.strip()
        main_factors = [item.strip() for item in main_factors]
        conclusion = conclusion.strip()
        next_checks = [item.strip() for item in next_checks]

        conclusion = self._add_ranking_scope(
            final_answer=conclusion,
            evidence=evidence,
        )
        conclusion = self._add_category_delivery_details(
            final_answer=conclusion,
            evidence=evidence,
        )
        conclusion = self._add_seller_reviews_caveat(
            final_answer=conclusion,
            evidence=evidence,
        )
        conclusion = self._add_region_delivery_details(
            final_answer=conclusion,
            evidence=evidence,
        )
        conclusion = self._add_delivery_rating_details(
            final_answer=conclusion,
            evidence=evidence,
        )
        conclusion = self._add_category_sales_details(
            final_answer=conclusion,
            evidence=evidence,
        )

        final_answer = self._format_structured_answer(
            short_summary=short_summary,
            main_factors=main_factors,
            conclusion=conclusion,
            next_checks=next_checks,
        )
        known_evidence_ids = {
            item.evidence_id for item in evidence
        }

        findings = [
            self._create_finding(
                raw_finding=raw_finding,
                known_evidence_ids=known_evidence_ids,
            )
            for raw_finding in raw_findings
        ]

        return AnalysisResult(
            findings=findings,
            final_answer=final_answer,
            short_summary=short_summary,
            main_factors=main_factors,
            conclusion=conclusion,
            next_checks=next_checks,
        )

    @staticmethod
    def _format_structured_answer(
        short_summary: str,
        main_factors: list[str],
        conclusion: str,
        next_checks: list[str],
    ) -> str:
        """Собрать текстовую версию ответа для CLI и старых клиентов."""

        factors = "\n".join(
            f"{index}. {factor}"
            for index, factor in enumerate(main_factors, start=1)
        ) or "Нет подтверждённых факторов."
        checks = "\n".join(
            f"- {check}" for check in next_checks
        ) or "- Дополнительные проверки не требуются."

        return (
            f"Краткий вывод\n{short_summary}\n\n"
            f"Основные факторы\n{factors}\n\n"
            f"Вывод\n{conclusion}\n\n"
            f"Что проверить дальше\n{checks}"
        )

    @staticmethod
    def _add_ranking_scope(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Добавить точные границы выборки продавцов в бизнес-ответ."""

        ranking_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name
                == "find_high_sales_low_rating_sellers"
            ),
            None,
        )

        if ranking_evidence is None:
            return final_answer

        data = ranking_evidence.data
        pool_size = data.get("candidate_pool_size")
        evaluated = data.get("evaluated_sellers")
        threshold = data.get("rating_threshold")
        threshold_source = data.get("threshold_source")

        if not isinstance(pool_size, int) or not isinstance(evaluated, int):
            return final_answer

        try:
            formatted_threshold = f"{float(threshold):.2f}"
        except (TypeError, ValueError):
            formatted_threshold = str(threshold)

        if threshold_source == "market_average_rating":
            threshold_description = (
                "среднего рейтинга по магазину "
                f"({formatted_threshold})"
            )
        else:
            threshold_description = (
                f"заданного порога ({formatted_threshold})"
            )

        scope = (
            f"Критерий: оценены {evaluated} продавцов из топ-{pool_size} "
            "по выручке; низким считался рейтинг ниже "
            f"{threshold_description}."
        )

        return f"{final_answer} {scope}"

    @staticmethod
    def _add_category_delivery_details(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Гарантированно добавить числа к рейтингу задержек категорий."""

        ranking_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name == "get_category_delivery_ranking"
            ),
            None,
        )
        if ranking_evidence is None:
            return final_answer

        data = ranking_evidence.data
        categories = data.get("categories")
        min_orders = data.get("min_orders")
        ranking_metric = data.get("ranking_metric")
        if not isinstance(categories, list) or not categories:
            return final_answer

        if ranking_metric == "delayed_share":
            metric_description = "доле задержанных заказов"
        elif ranking_metric == "delayed_orders":
            metric_description = "количеству задержанных заказов"
        else:
            metric_description = "среднему времени доставки"
        details: list[str] = []

        for category in categories[:3]:
            if not isinstance(category, dict):
                continue
            try:
                percentage = float(category["delayed_percentage"])
                delayed = int(category["delayed_orders"])
                total = int(category["total_delivered_orders"])
                name = str(category["category_name"])
            except (KeyError, TypeError, ValueError):
                continue

            details.append(
                f"{name} — {percentage:.2f}% ({delayed} из {total})"
            )

        if not details:
            return final_answer

        scope = (
            f"Рейтинг построен по {metric_description} среди категорий "
            f"минимум с {min_orders} доставленными заказами: "
            f"{'; '.join(details)}."
        )
        return f"{final_answer} {scope}"

    @staticmethod
    def _add_seller_reviews_caveat(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Уточнить границы выводов по негативным отзывам продавца."""

        review_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name == "get_seller_negative_reviews"
            ),
            None,
        )
        if review_evidence is None:
            return final_answer

        count = review_evidence.data.get("count")
        requested_limit = review_evidence.data.get("requested_limit")
        caveat = (
            f"Это возможные факторы по выборке из {count} последних "
            f"негативных отзывов (лимит {requested_limit}), а не доказанная "
            "причинная связь. Отзыв относится ко всему заказу, который мог "
            "содержать товары нескольких продавцов."
        )
        return f"{final_answer} {caveat}"

    @staticmethod
    def _add_region_delivery_details(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Гарантированно добавить числа к рейтингу задержек регионов."""

        ranking_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name == "get_region_delivery_ranking"
            ),
            None,
        )
        if ranking_evidence is None:
            return final_answer

        data = ranking_evidence.data
        regions = data.get("regions")
        min_orders = data.get("min_orders")
        ranking_metric = data.get("ranking_metric")
        if not isinstance(regions, list) or not regions:
            return final_answer

        metric_description = (
            "доле задержанных заказов"
            if ranking_metric == "delayed_share"
            else "количеству задержанных заказов"
        )
        details: list[str] = []

        for region in regions[:3]:
            if not isinstance(region, dict):
                continue
            try:
                total = int(region["total_delivered_orders"])
                name = str(region["region"])
            except (KeyError, TypeError, ValueError):
                continue

            if ranking_metric == "average_delivery_days":
                try:
                    average_days = float(region["average_delivery_days"])
                except (KeyError, TypeError, ValueError):
                    continue
                details.append(
                    f"{name} — {average_days:.2f} дня, заказов {total}"
                )
            else:
                try:
                    percentage = float(region["delayed_percentage"])
                    delayed = int(region["delayed_orders"])
                except (KeyError, TypeError, ValueError):
                    continue
                details.append(
                    f"{name} — {percentage:.2f}% ({delayed} из {total})"
                )

        if not details:
            return final_answer

        scope = (
            f"Рейтинг построен по {metric_description} среди регионов "
            f"минимум со {min_orders} доставленными заказами: "
            f"{'; '.join(details)}."
        )
        return f"{final_answer} {scope}"

    @staticmethod
    def _add_delivery_rating_details(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Гарантированно добавить числа и ограничение корреляционного вывода."""

        relationship_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name
                == "analyze_delivery_rating_relationship"
            ),
            None,
        )
        if relationship_evidence is None:
            return final_answer

        data = relationship_evidence.data
        seller_id = data.get("seller_id")
        analysis_scope = data.get("analysis_scope")
        try:
            delayed_score = float(data["delayed_average_score"])
            on_time_score = float(data["on_time_average_score"])
            delayed_negative = float(data["delayed_negative_percentage"])
            on_time_negative = float(data["on_time_negative_percentage"])
            status_correlation = float(
                data["delay_status_score_correlation"]
            )
            days_correlation = float(
                data["delay_days_score_correlation"]
            )
        except (KeyError, TypeError, ValueError):
            return final_answer

        details = (
            (
                f"Расчёт выполнен только по заказам продавца {seller_id}. "
                if analysis_scope == "seller_orders" and seller_id
                else "Расчёт выполнен по всем заказам магазина. "
            )
            + "С задержкой: средняя оценка "
            f"{delayed_score:.2f}, негативных отзывов "
            f"{delayed_negative:.2f}%; вовремя: средняя оценка "
            f"{on_time_score:.2f}, негативных отзывов "
            f"{on_time_negative:.2f}%. Корреляция оценки с фактом задержки "
            f"{status_correlation:.4f}, с числом дней задержки "
            f"{days_correlation:.4f}. Это статистическая связь, а не "
            "доказательство причинности."
        )
        return f"{final_answer} {details}"

    @staticmethod
    def _add_category_sales_details(
        final_answer: str,
        evidence: list[Evidence],
    ) -> str:
        """Гарантированно добавить числа к рейтингу продаж категорий."""

        ranking_evidence = next(
            (
                item
                for item in evidence
                if item.tool_name == "get_category_sales_ranking"
            ),
            None,
        )
        if ranking_evidence is None:
            return final_answer

        data = ranking_evidence.data
        categories = data.get("categories")
        ranking_metric = data.get("ranking_metric")
        revenue_definition = data.get("revenue_definition")
        currency = data.get("currency")
        if not isinstance(categories, list) or not categories:
            return final_answer

        normalized_answer = final_answer.lower()
        top_categories = [
            category
            for category in categories[:3]
            if isinstance(category, dict)
        ]
        has_all_category_names = all(
            str(category.get("category_name", "")).lower()
            in normalized_answer
            for category in top_categories
        )
        has_metric = (
            isinstance(ranking_metric, str)
            and ranking_metric.lower() in normalized_answer
        )
        has_revenue_definition = (
            "price" in normalized_answer
            and "freight_value" in normalized_answer
        )

        # Не дублируем рейтинг, если Critic уже включил все обязательные детали.
        if (
            top_categories
            and has_all_category_names
            and has_metric
            and has_revenue_definition
        ):
            return final_answer

        details: list[str] = []
        for category in categories[:3]:
            if not isinstance(category, dict):
                continue
            try:
                name = str(category["category_name"])
                revenue = float(category["total_revenue"])
                orders = int(category["total_orders"])
            except (KeyError, TypeError, ValueError):
                continue

            formatted_revenue = (
                f"{revenue:,.2f}"
                .replace(",", " ")
                .replace(".", ",")
            )
            if currency == "BRL":
                formatted_revenue = f"R$ {formatted_revenue}"
            details.append(
                f"{name} — выручка {formatted_revenue}, "
                f"заказов {orders}"
            )

        if not details:
            return final_answer

        scope = (
            f"Рейтинг построен по {ranking_metric}: {'; '.join(details)}. "
            f"Определение выручки: {revenue_definition}."
        )
        return f"{final_answer} {scope}"

    def _create_finding(
        self,
        raw_finding: Any,
        known_evidence_ids: set[str],
    ) -> ProposedFinding:
        """Проверить один вывод, созданный моделью."""

        if not isinstance(raw_finding, dict):
            raise ValueError(
                "Каждый finding должен быть JSON-объектом"
            )

        statement = raw_finding.get("statement")
        evidence_ids = raw_finding.get("evidence_ids")
        confidence_value = raw_finding.get("confidence")
        is_hypothesis = raw_finding.get(
            "is_hypothesis",
            False,
        )

        if not isinstance(statement, str):
            raise ValueError(
                "У finding отсутствует statement"
            )

        if not statement.strip():
            raise ValueError(
                "Текст finding не должен быть пустым"
            )

        if not isinstance(evidence_ids, list):
            raise ValueError(
                "evidence_ids должен быть списком"
            )

        if not all(
            isinstance(item, str)
            for item in evidence_ids
        ):
            raise ValueError(
                "Все evidence_id должны быть строками"
            )

        unknown_ids = (
            set(evidence_ids) - known_evidence_ids
        )

        if unknown_ids:
            raise ValueError(
                "Critic сослался на неизвестные Evidence: "
                + ", ".join(sorted(unknown_ids))
            )

        if not isinstance(is_hypothesis, bool):
            raise ValueError(
                "is_hypothesis должен быть true или false"
            )

        if not evidence_ids and not is_hypothesis:
            raise ValueError(
                "Фактический вывод должен иметь Evidence"
            )

        try:
            confidence = ConfidenceLevel(
                confidence_value
            )
        except (ValueError, TypeError) as error:
            raise ValueError(
                f"Некорректный confidence: {confidence_value}"
            ) from error

        if (
            is_hypothesis
            and confidence is ConfidenceLevel.HIGH
        ):
            raise ValueError(
                "Гипотеза не может иметь confidence=high"
            )

        return ProposedFinding(
            statement=statement.strip(),
            evidence_ids=evidence_ids,
            confidence=confidence,
            is_hypothesis=is_hypothesis,
        )
