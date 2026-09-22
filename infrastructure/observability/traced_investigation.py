"""Langfuse-трассировка полного LangChain-исследования."""

from langchain_core.runnables import RunnableConfig
from langfuse import observe, propagate_attributes
from langfuse.langchain import CallbackHandler

from application.investigate.use_cases import InvestigateQuestion
from domain.investigation.entities import Investigation


class TracedInvestigateQuestion:
    """Добавить Langfuse-трассировку к use case исследования."""

    def __init__(
        self,
        use_case: InvestigateQuestion,
        langfuse_handler: CallbackHandler | None = None,
    ) -> None:
        self.use_case = use_case
        self.langfuse_handler = langfuse_handler

    @observe(name="olist-investigation")
    async def execute(
        self,
        question: str,
        session_id: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Investigation:
        """Выполнить исследование внутри одной Langfuse-трассы."""

        config: RunnableConfig = {
            "run_name": "olist-investigation",
        }

        if self.langfuse_handler is not None:
            config["callbacks"] = [self.langfuse_handler]

        if session_id is None:
            return await self.use_case.execute(
                question,
                history=history,
                config=config,
            )

        with propagate_attributes(
            session_id=session_id,
            tags=["olist-chat", "langchain"],
        ):
            return await self.use_case.execute(
                question,
                history=history,
                config=config,
            )
