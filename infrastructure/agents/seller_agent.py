"""Seller Agent, построенный средствами LangChain."""

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from infrastructure.mcp.langchain_client import load_seller_tools


SELLER_AGENT_PROMPT = """
Ты Seller Agent аналитической системы Olist.

Твоя область ответственности:
- основная информация о продавцах;
- местоположение продавцов;
- ассортимент, категории и уникальные товары продавца;
- наиболее продаваемые товары продавца;
- поиск продавцов по комплексным показателям.

Используй только предоставленные MCP-инструменты.
Не придумывай идентификаторы, числа и факты.
Если данных недостаточно, прямо сообщи об ограничении.
Отвечай только на основании результатов инструментов.
""".strip()


async def create_seller_agent(
    model: BaseChatModel,
) -> Runnable:
    """Создать LangChain-агента с инструментами Seller MCP."""

    tools = await load_seller_tools()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SELLER_AGENT_PROMPT,
        name="seller_agent",
    )
