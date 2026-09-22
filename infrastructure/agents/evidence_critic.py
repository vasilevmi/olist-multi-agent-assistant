"""LangChain-агент для проверки Evidence и подготовки итогового ответа."""

from typing import Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, model_validator


class CriticFinding(BaseModel):
    """Один факт или гипотеза, сформированные Critic-агентом."""

    statement: str = Field(
        description="Понятный пользователю вывод.",
        min_length=1,
    )
    evidence_ids: list[str] = Field(
        description="ID доказательств, подтверждающих вывод.",
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Уверенность в выводе.",
    )
    is_hypothesis: bool = Field(
        description="True, если это возможное объяснение, а не факт.",
    )

    @model_validator(mode="after")
    def validate_grounding(self) -> "CriticFinding":
        """Не позволять выдавать неподтверждённый вывод за факт."""

        if not self.is_hypothesis and not self.evidence_ids:
            raise ValueError("Факт должен ссылаться хотя бы на одно Evidence")

        if self.is_hypothesis and self.confidence == "high":
            raise ValueError("Гипотеза не может иметь confidence=high")

        return self


class CriticResponse(BaseModel):
    """Структурированный результат проверки исследования."""

    findings: list[CriticFinding] = Field(
        description="Проверенные факты и явно обозначенные гипотезы.",
    )
    short_summary: str = Field(
        description=(
            "Основной самостоятельный ответ пользователю из 3–5 предложений."
        ),
        min_length=1,
    )
    main_factors: list[str] = Field(
        description="Ключевые подтверждённые факторы с конкретными значениями.",
    )
    conclusion: str = Field(
        description="Интерпретация результата и границы сделанного вывода.",
        min_length=1,
    )
    next_checks: list[str] = Field(
        description="Полезные последующие проверки, если они действительно нужны.",
    )


EVIDENCE_CRITIC_PROMPT = """
Ты Critic / Evidence Agent аналитической системы Olist.

На вход ты получаешь:
- исходный вопрос пользователя;
- список Evidence от MCP-инструментов;
- возможные ограничения исследования.

Твоя задача:
1. Ответить именно на исходный вопрос.
2. Использовать только факты из переданных Evidence.
3. Для каждого факта указать существующие evidence_ids.
4. Не придумывать числа, валюту, причины, возвраты или отсутствующие данные.
5. Причинное объяснение без прямого доказательства помечать как гипотезу.
6. Гипотезе назначать confidence low или medium, но никогда high.
7. Confidence high использовать только для значений, прямо указанных в Evidence.
8. Если данных недостаточно, дать максимально полезный частичный ответ и честно
   назвать ограничение — не считать всё исследование неуспешным.
9. Не повторять один и тот же текст в разных разделах.
10. Отвечать на языке пользователя.

short_summary — главный ответ, который первым увидит пользователь. Он должен быть
понятным без чтения технических деталей. main_factors содержит основные факты,
conclusion — аккуратную интерпретацию, next_checks — только осмысленные следующие
проверки. Технические имена MCP-инструментов допустимы в conclusion для аудита.
""".strip()


def create_evidence_critic(model: BaseChatModel) -> Runnable:
    """Создать Critic-агента со строгой схемой результата."""

    return create_agent(
        model=model,
        tools=[],
        system_prompt=EVIDENCE_CRITIC_PROMPT,
        response_format=ToolStrategy(CriticResponse),
        name="evidence_critic",
    )
