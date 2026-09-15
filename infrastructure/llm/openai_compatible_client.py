"""Клиент любой LLM с OpenAI-совместимым HTTP API."""

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI, OpenAIError

from infrastructure.observability.run_metrics import RunMetrics


class OpenAICompatibleClient:
    """Отправляет Chat Completions запросы выбранному LLM-провайдеру."""

    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 90.0,
        metrics: RunMetrics | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("LLM_API_KEY не указан")
        if not model:
            raise ValueError("LLM_MODEL не указан")
        if not base_url:
            raise ValueError("LLM_BASE_URL не указан")

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.metrics = metrics
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=timeout,
        )

    @classmethod
    def from_env(
        cls,
        metrics: RunMetrics | None = None,
    ) -> "OpenAICompatibleClient":
        """Создать клиент из универсальных переменных файла .env."""

        load_dotenv()

        # GROQ_* оставлены как временная обратная совместимость.
        return cls(
            api_key=(
                os.getenv("LLM_API_KEY")
                or os.getenv("GROQ_API_KEY", "")
            ),
            model=(
                os.getenv("LLM_MODEL")
                or os.getenv("GROQ_MODEL", "")
            ),
            base_url=os.getenv(
                "LLM_BASE_URL",
                cls.GROQ_BASE_URL,
            ),
            metrics=metrics,
        )

    @staticmethod
    def _remove_code_fence(content: str) -> str:
        """Убрать ```json, если модель всё же обернула ответ в Markdown."""

        stripped = content.strip()
        if not stripped.startswith("```"):
            return stripped

        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Получить JSON с fallback для разных OpenAI-совместимых API."""

        response_formats: list[dict[str, Any] | None] = []
        if json_schema is not None:
            response_formats.append(
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "llm_response",
                        "strict": True,
                        "schema": json_schema,
                    },
                }
            )
        response_formats.extend(
            [
                {"type": "json_object"},
                None,
            ]
        )

        if self.metrics is not None:
            self.metrics.record_llm_call()

        last_error: Exception | None = None

        for format_index, response_format in enumerate(response_formats):
            for attempt in range(2):
                retry_instruction = (
                    " Верни короткий, завершённый и валидный JSON без "
                    "Markdown и без пояснений вне JSON."
                    if attempt > 0 or response_format is None
                    else ""
                )
                request: dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt + retry_instruction,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "temperature": 0,
                    "max_tokens": max_tokens,
                }
                if response_format is not None:
                    request["response_format"] = response_format

                try:
                    completion = self.client.chat.completions.create(**request)
                except APIStatusError as error:
                    last_error = error
                    if error.status_code == 400:
                        # Некоторые совместимые API не поддерживают
                        # json_schema или response_format.
                        break
                    raise RuntimeError(
                        f"Не удалось получить ответ от LLM: {error}"
                    ) from error
                except OpenAIError as error:
                    raise RuntimeError(
                        f"Не удалось получить ответ от LLM: {error}"
                    ) from error

                content = completion.choices[0].message.content
                if content is None:
                    last_error = RuntimeError("LLM вернула пустой ответ")
                    continue

                try:
                    result = json.loads(self._remove_code_fence(content))
                except json.JSONDecodeError as error:
                    last_error = error
                    continue

                if isinstance(result, dict):
                    return result

                last_error = RuntimeError(
                    "Ответ LLM должен быть JSON-объектом"
                )

            if format_index + 1 < len(response_formats):
                continue

        raise RuntimeError(
            "LLM не вернула корректный JSON"
        ) from last_error
