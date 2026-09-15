"""MCP-сервер инструментов каталога."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import MCPServer
from pydantic import BaseModel
from sqlalchemy import create_engine

from application.catalog.use_cases import (
    GetCategory,
    GetCategoryProducts,
    GetProduct,
    GetProductStatistics,
)
from domain.catalog.entities import Product
from infrastructure.postgres.catalog_repository import (
    PostgresCatalogRepository,
)


class ProductResult(BaseModel):
    """Карточка товара для ответа MCP."""

    product_id: str
    category_name_original: str | None
    category_name_english: str | None
    name_length: int | None
    description_length: int | None
    photos_quantity: int | None
    weight_g: str | None
    length_cm: str | None
    height_cm: str | None
    width_cm: str | None


class CategoryResult(BaseModel):
    """Информация о категории."""

    category_name_original: str
    category_name_english: str
    total_products: int


class CategoryProductsResult(BaseModel):
    """Список товаров выбранной категории."""

    category_name: str
    count: int
    products: list[ProductResult]


class ProductStatisticsResult(BaseModel):
    """Показатели завершённых продаж товара."""

    product_id: str
    total_orders: int
    total_items: int
    total_revenue: str
    average_price: str
    unique_sellers: int


def _parse_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Дата должна быть в формате YYYY-MM-DD") from error


def _to_product_result(product: Product) -> ProductResult:
    """Преобразовать доменный Product в результат MCP."""
    return ProductResult(
        product_id=product.product_id,
        category_name_original=product.category_name_original,
        category_name_english=product.category_name_english,
        name_length=product.name_length,
        description_length=product.description_length,
        photos_quantity=product.photos_quantity,
        weight_g=str(product.weight_g) if product.weight_g is not None else None,
        length_cm=(
            str(product.length_cm) if product.length_cm is not None else None
        ),
        height_cm=(
            str(product.height_cm) if product.height_cm is not None else None
        ),
        width_cm=str(product.width_cm) if product.width_cm is not None else None,
    )


project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

database_url = (
    f"postgresql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(database_url)
repository = PostgresCatalogRepository(engine)
get_product_use_case = GetProduct(repository)
get_category_use_case = GetCategory(repository)
get_category_products_use_case = GetCategoryProducts(repository)
get_product_statistics_use_case = GetProductStatistics(repository)

mcp = MCPServer("Catalog MCP")


@mcp.tool()
def get_product(product_id: str) -> ProductResult:
    """Получить карточку товара по product_id."""
    product = get_product_use_case.execute(product_id)
    if product is None:
        raise ValueError(f"Товар {product_id} не найден")
    return _to_product_result(product)


@mcp.tool()
def get_category(category_name: str) -> CategoryResult:
    """Получить категорию по английскому или исходному названию."""
    category = get_category_use_case.execute(category_name)
    if category is None:
        raise ValueError(f"Категория {category_name} не найдена")
    return CategoryResult(
        category_name_original=category.category_name_original,
        category_name_english=category.category_name_english,
        total_products=category.total_products,
    )


@mcp.tool()
def get_category_products(
    category_name: str,
    limit: int = 20,
) -> CategoryProductsResult:
    """Получить товары выбранной категории."""
    products = get_category_products_use_case.execute(category_name, limit)
    if not products:
        raise ValueError(f"Товары категории {category_name} не найдены")
    return CategoryProductsResult(
        category_name=category_name,
        count=len(products),
        products=[_to_product_result(product) for product in products],
    )


@mcp.tool()
def get_product_statistics(
    product_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ProductStatisticsResult:
    """Получить статистику завершённых продаж товара за период."""
    statistics = get_product_statistics_use_case.execute(
        product_id,
        _parse_date(start_date),
        _parse_date(end_date),
    )
    if statistics is None:
        raise ValueError(f"Товар {product_id} не найден")
    return ProductStatisticsResult(
        product_id=statistics.product_id,
        total_orders=statistics.total_orders,
        total_items=statistics.total_items,
        total_revenue=str(statistics.total_revenue),
        average_price=str(statistics.average_price),
        unique_sellers=statistics.unique_sellers,
    )


if __name__ == "__main__":
    mcp.run()
