"""Стандартные DeepEval-метрики для системы Olist."""

from deepeval.metrics import (
    BaseMetric,
    FaithfulnessMetric,
    GEval,
    ToolCorrectnessMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import SingleTurnParams


def build_metrics(
    judge: DeepEvalBaseLLM,
    *,
    research: bool,
) -> list[BaseMetric]:
    """Выбрать готовые DeepEval-метрики для одного тест-кейса."""

    metrics: list[BaseMetric] = [
        ToolCorrectnessMetric(
            threshold=1.0,
            model=judge,
            include_reason=True,
        ),
        GEval(
            name="Answer Relevancy",
            criteria=(
                "Оцени, отвечает ли текст прямо на поставленный вопрос. Главный "
                "результат должен быть сформулирован явно и без необходимости "
                "догадываться. Не снижай оценку за подтверждающие числа, основные "
                "факторы, ограничения данных и уместные следующие проверки, если "
                "они связаны с вопросом. Снижай оценку за уход от вопроса, подмену "
                "запрошенного показателя другим или отсутствие самого ответа."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
            ],
            threshold=0.7,
            model=judge,
            async_mode=True,
        ),
        FaithfulnessMetric(
            threshold=0.8,
            model=judge,
            include_reason=True,
            async_mode=True,
        ),
    ]

    if not research:
        metrics.append(
            GEval(
                name="Business Correctness",
                criteria=(
                    "Сравни фактический ответ с эталонным ответом. Проверь имена "
                    "объектов, числовые значения, порядок лидеров, пороги и границы "
                    "выборки. Незначительная разница округления допустима, если она "
                    "не меняет бизнес-смысл. Не засчитывай ответ, который противоречит "
                    "эталонным фактам или пропускает главный результат."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.EXPECTED_OUTPUT,
                ],
                threshold=0.8,
                model=judge,
                async_mode=True,
            )
        )
        return metrics

    metrics.extend(
        [
            GEval(
                name="Research Completeness",
                criteria=(
                    "Оцени, насколько полно фактический ответ выполняет именно "
                    "запрос пользователя. Все явно запрошенные объекты, показатели, "
                    "сравнения и связи должны быть рассмотрены. Ответ должен "
                    "содержать конкретные результаты, а при нехватке данных — "
                    "честно называть ограничение. Не требуй информацию, которую "
                    "пользователь не запрашивал."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.RETRIEVAL_CONTEXT,
                ],
                threshold=0.7,
                model=judge,
                async_mode=True,
            ),
            GEval(
                name="Facts And Hypotheses",
                criteria=(
                    "Проверь аналитическую осторожность ответа. Числа и факты "
                    "должны подтверждаться retrieval context. Причинные объяснения "
                    "без прямого доказательства должны называться гипотезами, "
                    "возможными факторами или статистической связью, а не доказанной "
                    "причиной. Ответ не должен придумывать отсутствующие данные или "
                    "скрывать ограничения."
                ),
                evaluation_params=[
                    SingleTurnParams.INPUT,
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.RETRIEVAL_CONTEXT,
                ],
                threshold=0.8,
                model=judge,
                async_mode=True,
            ),
        ]
    )

    return metrics
