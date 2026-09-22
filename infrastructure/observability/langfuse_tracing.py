"""Подключение трассировки Langfuse."""

import os
from dotenv import load_dotenv
from langfuse import get_client
from langfuse.langchain import CallbackHandler


def create_langfuse_handler() -> CallbackHandler | None:
    """Создать обработчик Langfuse, если указаны ключи."""
    load_dotenv()

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        return None

    get_client()

    return CallbackHandler()