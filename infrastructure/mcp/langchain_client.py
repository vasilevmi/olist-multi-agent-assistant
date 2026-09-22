"""Подключение LangChain к MCP-серверам приложения."""

import asyncio
import os
import sys
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MCP_ENVIRONMENT_VARIABLES = (
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
)


def _mcp_environment() -> dict[str, str]:
    """Передать дочернему MCP-процессу БД и базовое окружение ОС."""

    return {
        name: value
        for name in MCP_ENVIRONMENT_VARIABLES
        if (value := os.getenv(name)) is not None
    }


def _stdio_connection(module: str) -> StdioConnection:
    """Собрать конфигурацию локального MCP-сервера."""

    return {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", module],
        "cwd": str(PROJECT_ROOT),
        "env": _mcp_environment(),
    }


def create_mcp_client() -> MultiServerMCPClient:
    """Создать MCP-клиент для доступных серверов приложения."""

    return MultiServerMCPClient(
        {
            "seller": _stdio_connection(
                "infrastructure.mcp.seller_server"
            ),
            "sales": _stdio_connection(
                "infrastructure.mcp.sales_server"
            ),
            "catalog": _stdio_connection(
                "infrastructure.mcp.catalog_server"
            ),
            "delivery": _stdio_connection(
                "infrastructure.mcp.delivery_server"
            ),
            "reviews": _stdio_connection(
                "infrastructure.mcp.reviews_server"
            ),
        },
        handle_tool_errors=True,
    )


async def load_seller_tools() -> list[BaseTool]:
    """Загрузить инструменты Seller MCP как LangChain Tools."""

    client = create_mcp_client()
    return await client.get_tools(server_name="seller")


async def load_sales_tools() -> list[BaseTool]:
    """Загрузить инструменты продаж и каталога."""

    client = create_mcp_client()
    sales_tools, catalog_tools = await asyncio.gather(
        client.get_tools(server_name="sales"),
        client.get_tools(server_name="catalog"),
    )
    return [*sales_tools, *catalog_tools]


async def load_delivery_tools() -> list[BaseTool]:
    """Загрузить инструменты Delivery MCP."""

    client = create_mcp_client()
    return await client.get_tools(server_name="delivery")


async def load_reviews_tools() -> list[BaseTool]:
    """Загрузить инструменты Reviews MCP."""

    client = create_mcp_client()
    return await client.get_tools(server_name="reviews")
