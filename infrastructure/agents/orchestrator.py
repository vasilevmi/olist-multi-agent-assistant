"""Orchestrator мультиагентной системы на LangChain."""

import asyncio

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from infrastructure.agents.delegation_tools import (
    create_delegation_tools,
)
from infrastructure.agents.delivery_agent import create_delivery_agent
from infrastructure.agents.reviews_agent import create_reviews_agent
from infrastructure.agents.sales_agent import create_sales_agent
from infrastructure.agents.seller_agent import create_seller_agent


ORCHESTRATOR_PROMPT = """
Ты Orchestrator мультиагентной аналитической системы Olist.

Твоя задача — понять вопрос пользователя, разделить исследование на
минимально необходимые специализированные задачи и делегировать их агентам.

Доступные специалисты:
- ask_sales_agent: продажи, заказы, выручка, товары и категории;
- ask_seller_agent: продавцы, местоположение и ассортимент;
- ask_delivery_agent: сроки, задержки и регионы доставки;
- ask_reviews_agent: отзывы, рейтинги и клиентский опыт.

Правила работы:
- для простого вопроса вызывай только одного подходящего агента;
- для комплексного вопроса можешь вызвать нескольких агентов;
- передавай каждому агенту только относящийся к нему контекст;
- сохраняй идентификаторы, даты, пороги и другие условия пользователя;
- не вызывай одного агента повторно с одинаковой задачей;
- не придумывай факты, числа и результаты инструментов;
- каждый аналитический вывод подтверждай полученными evidence;
- если данных недостаточно, явно укажи ограничение;
- отвечай на языке пользователя.

Результат каждого специалиста содержит поля answer и evidence.
Сформируй понятный ответ на вопрос пользователя только по этим данным.
""".strip()


async def create_orchestrator(
    model: BaseChatModel,
) -> Runnable:
    """Создать Orchestrator и его специализированных агентов."""

    (
        sales_agent,
        seller_agent,
        delivery_agent,
        reviews_agent,
    ) = await asyncio.gather(
        create_sales_agent(model),
        create_seller_agent(model),
        create_delivery_agent(model),
        create_reviews_agent(model),
    )

    delegation_tools = create_delegation_tools(
        sales_agent=sales_agent,
        seller_agent=seller_agent,
        delivery_agent=delivery_agent,
        reviews_agent=reviews_agent,
    )

    return create_agent(
        model=model,
        tools=delegation_tools,
        system_prompt=ORCHESTRATOR_PROMPT,
        name="orchestrator",
    )
