"""Создание языковой модели через LangChain."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def create_chat_model() -> ChatOpenAI:
    """Создать модель из настроек файла .env."""
    load_dotenv()

    api_key = os.getenv("LLM_API_KEY", "")
    model_name = os.getenv("LLM_MODEL", "")
    base_url = os.getenv("LLM_BASE_URL", "")

    if not api_key:
        raise ValueError("LLM_API_KEY не указан")

    if not model_name:
        raise ValueError("LLM_MODEL не указан")

    if not base_url:
        raise ValueError("LLM_BASE_URL не указан")

    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        base_url=base_url.rstrip("/"),
        temperature=0,
        timeout=90,
        max_retries=2,
    )
