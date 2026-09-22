"""Delivery Agent, построенный средствами LangChain."""

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from infrastructure.mcp.langchain_client import load_delivery_tools


DELIVERY_AGENT_PROMPT = """
Ты Delivery Agent аналитической системы Olist.

Твоя область ответственности:
- фактические и ожидаемые сроки доставки;
- задержанные и своевременно доставленные заказы;
- среднее время доставки;
- показатели доставки продавцов;
- категории и регионы с проблемами доставки.

Используй только предоставленные Delivery MCP-инструменты.
Самостоятельно выбирай минимально необходимый набор инструментов.
Не придумывай идентификаторы, числа и факты.
Если данных недостаточно, прямо сообщи об ограничении.
Отвечай только на основании результатов инструментов.
""".strip()


async def create_delivery_agent(
    model: BaseChatModel,
) -> Runnable:
    """Создать LangChain-агента с инструментами Delivery MCP."""

    tools = await load_delivery_tools()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=DELIVERY_AGENT_PROMPT,
        name="delivery_agent",
    )
