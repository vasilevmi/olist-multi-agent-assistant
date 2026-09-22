"""Customer Experience Agent, построенный средствами LangChain."""

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from infrastructure.mcp.langchain_client import load_reviews_tools


REVIEWS_AGENT_PROMPT = """
Ты Customer Experience Agent аналитической системы Olist.

Твоя область ответственности:
- отзывы и оценки клиентов;
- средний рейтинг и распределение оценок;
- негативные отзывы;
- рейтинги продавцов и товарных категорий;
- связь клиентских оценок с доставкой и другими факторами.

Используй только предоставленные Reviews MCP-инструменты.
Самостоятельно выбирай минимально необходимый набор инструментов.
Не придумывай идентификаторы, числа и факты.
Если данных недостаточно, прямо сообщи об ограничении.
Отвечай только на основании результатов инструментов.
""".strip()


async def create_reviews_agent(
    model: BaseChatModel,
) -> Runnable:
    """Создать LangChain-агента с инструментами Reviews MCP."""

    tools = await load_reviews_tools()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=REVIEWS_AGENT_PROMPT,
        name="reviews_agent",
    )
