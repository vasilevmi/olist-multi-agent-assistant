"""OpenAI-compatible LLM-судья для смысловых метрик DeepEval."""

import json
from typing import Any

from deepeval.models import DeepEvalBaseLLM
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from infrastructure.llm.langchain_client import create_chat_model


def _content_to_text(content: Any) -> str:
    """Привести текстовый или блочный ответ LangChain к строке."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(
                        json.dumps(block, ensure_ascii=False, default=str)
                    )
        return "\n".join(parts)

    return str(content)


class LangChainDeepEvalJudge(DeepEvalBaseLLM):
    """Адаптировать LangChain ChatModel к интерфейсу DeepEvalBaseLLM."""

    def __init__(
        self,
        model: BaseChatModel,
        model_name: str = "openai-compatible-judge",
    ) -> None:
        self.model = model
        self.model_name = model_name

    def load_model(self) -> BaseChatModel:
        """Вернуть LangChain-модель, выполняющую оценивание."""

        return self.model

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel] | BaseModel | None = None,
    ) -> str | BaseModel:
        """Синхронно получить обычный или структурированный вердикт."""

        model = self.load_model()

        if schema is not None:
            schema_type = schema if isinstance(schema, type) else type(schema)
            structured_model = model.with_structured_output(schema_type)
            result = structured_model.invoke(prompt)
            if isinstance(result, schema_type):
                return result
            return schema_type.model_validate(result)

        response = model.invoke(prompt)
        return _content_to_text(response.content)

    async def a_generate(
        self,
        prompt: str,
        schema: type[BaseModel] | BaseModel | None = None,
    ) -> str | BaseModel:
        """Асинхронно получить обычный или структурированный вердикт."""

        model = self.load_model()

        if schema is not None:
            schema_type = schema if isinstance(schema, type) else type(schema)
            structured_model = model.with_structured_output(schema_type)
            result = await structured_model.ainvoke(prompt)
            if isinstance(result, schema_type):
                return result
            return schema_type.model_validate(result)

        response = await model.ainvoke(prompt)
        return _content_to_text(response.content)

    def get_model_name(self) -> str:
        """Название судьи для отчётов DeepEval."""

        return self.model_name


def create_deepeval_judge() -> LangChainDeepEvalJudge:
    """Создать судью из тех же OpenAI-compatible переменных .env."""

    model = create_chat_model()
    configured_name = getattr(model, "model_name", None)

    return LangChainDeepEvalJudge(
        model=model,
        model_name=(
            f"{configured_name}-judge"
            if isinstance(configured_name, str) and configured_name
            else "openai-compatible-judge"
        ),
    )
