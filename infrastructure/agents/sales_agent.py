"""Sales Agent, построенный средствами LangChain."""

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from infrastructure.mcp.langchain_client import load_sales_tools


SALES_AGENT_PROMPT = """
Ты Sales Agent аналитической системы Olist.

Твоя область ответственности:
- продажи, заказы, товары и выручка;
- динамика и сравнение периодов;
- рейтинги продавцов по продажам;
- показатели товаров и товарных категорий;
- поиск лидеров и проблемных направлений продаж.

Используй только предоставленные MCP-инструменты продаж и каталога.
Самостоятельно выбирай минимально необходимый набор инструментов.
Не придумывай идентификаторы, числа и факты.
Если данных недостаточно, прямо сообщи об ограничении.
Отвечай только на основании результатов инструментов.
""".strip()


async def create_sales_agent(
    model: BaseChatModel,
) -> Runnable:
    """Создать LangChain-агента с инструментами Sales и Catalog MCP."""

    tools = await load_sales_tools()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SALES_AGENT_PROMPT,
        name="sales_agent",
    )
