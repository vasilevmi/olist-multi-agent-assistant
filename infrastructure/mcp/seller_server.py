"""MCP-сервер основной информации о продавцах."""

import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from sqlalchemy import create_engine

from application.seller.use_cases import (
    FindHighSalesLowRatingSellers,
    GetSeller,
    GetSellerCatalog,
    GetSellerTopProducts,
    GetSellersByLocation,
)
from domain.seller.entities import Seller
from infrastructure.postgres.seller_repository import PostgresSellerRepository


class SellerResult(BaseModel):
    """Карточка продавца для ответа MCP."""

    seller_id: str
    zip_code_prefix: str
    city: str
    state: str
    location: str


class SellersByLocationResult(BaseModel):
    """Список продавцов, найденных по местоположению."""

    state: str | None
    city: str | None
    count: int
    sellers: list[SellerResult]


class SellerCatalogResult(BaseModel):
    """Исторический ассортимент продавца."""

    seller_id: str
    total_categories: int
    total_unique_products: int
    listed_products: int
    categories: list[str]
    product_ids: list[str]


class SellerProductSalesResult(BaseModel):
    """Показатели одного товара в топе продавца."""

    product_id: str
    category_name: str | None
    total_orders: int
    total_items: int
    total_revenue: str
    average_price: str


class SellerTopProductsResult(BaseModel):
    """Товары продавца, отсортированные по выручке."""

    seller_id: str
    ranking_metric: str
    count: int
    products: list[SellerProductSalesResult]


class SellerSalesRatingResult(BaseModel):
    """Продажи и рейтинг одного продавца из выборки."""

    seller_id: str
    total_orders: int
    total_revenue: str
    average_rating: str
    total_reviews: int


class HighSalesLowRatingResult(BaseModel):
    """Результат поиска продавцов с высокой выручкой и низким рейтингом."""

    ranking_metric: str
    candidate_pool_size: int
    evaluated_sellers: int
    rating_threshold: str
    threshold_source: str
    market_average_rating: str
    count: int
    sellers: list[SellerSalesRatingResult]


def _to_seller_result(seller: Seller) -> SellerResult:
    return SellerResult(
        seller_id=seller.seller_id,
        zip_code_prefix=seller.zip_code_prefix,
        city=seller.city,
        state=seller.state,
        location=seller.location,
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
repository = PostgresSellerRepository(engine)
get_seller_use_case = GetSeller(repository)
get_sellers_by_location_use_case = GetSellersByLocation(repository)
get_seller_catalog_use_case = GetSellerCatalog(repository)
get_seller_top_products_use_case = GetSellerTopProducts(repository)
find_high_sales_low_rating_use_case = FindHighSalesLowRatingSellers(repository)

mcp = FastMCP("Seller MCP", log_level="WARNING")


@mcp.tool()
def get_seller(seller_id: str) -> SellerResult:
    """Получить основную информацию о продавце."""
    seller = get_seller_use_case.execute(seller_id)
    if seller is None:
        raise ValueError(f"Продавец {seller_id} не найден")
    return _to_seller_result(seller)


@mcp.tool()
def get_sellers_by_location(
    state: str | None = None,
    city: str | None = None,
    limit: int = 20,
) -> SellersByLocationResult:
    """Найти продавцов по штату и/или городу."""
    sellers = get_sellers_by_location_use_case.execute(state, city, limit)
    return SellersByLocationResult(
        state=state.upper() if state is not None else None,
        city=city,
        count=len(sellers),
        sellers=[_to_seller_result(seller) for seller in sellers],
    )


@mcp.tool()
def get_seller_catalog(
    seller_id: str,
    product_limit: int = 20,
) -> SellerCatalogResult:
    """Получить категории и уникальные товары продавца."""
    catalog = get_seller_catalog_use_case.execute(seller_id, product_limit)
    if catalog is None:
        raise ValueError(f"Продавец {seller_id} не найден")
    return SellerCatalogResult(
        seller_id=catalog.seller_id,
        total_categories=catalog.total_categories,
        total_unique_products=catalog.total_unique_products,
        listed_products=len(catalog.product_ids),
        categories=catalog.categories,
        product_ids=catalog.product_ids,
    )


@mcp.tool()
def get_seller_top_products(
    seller_id: str,
    limit: int = 10,
) -> SellerTopProductsResult:
    """Получить топ товаров продавца по выручке завершённых заказов."""
    products = get_seller_top_products_use_case.execute(seller_id, limit)
    if products is None:
        raise ValueError(f"Продавец {seller_id} не найден")
    return SellerTopProductsResult(
        seller_id=seller_id,
        ranking_metric="total_revenue",
        count=len(products),
        products=[
            SellerProductSalesResult(
                product_id=product.product_id,
                category_name=product.category_name,
                total_orders=product.total_orders,
                total_items=product.total_items,
                total_revenue=str(product.total_revenue),
                average_price=str(product.average_price),
            )
            for product in products
        ],
    )


@mcp.tool()
def find_high_sales_low_rating_sellers(
    candidate_limit: int = 20,
    result_limit: int = 10,
    max_rating: float | None = None,
) -> HighSalesLowRatingResult:
    """Найти продавцов из топа выручки с рейтингом ниже порога."""

    ranking = find_high_sales_low_rating_use_case.execute(
        candidate_limit=candidate_limit,
        result_limit=result_limit,
        max_rating=max_rating,
    )

    return HighSalesLowRatingResult(
        ranking_metric=ranking.ranking_metric,
        candidate_pool_size=ranking.candidate_pool_size,
        evaluated_sellers=ranking.evaluated_sellers,
        rating_threshold=str(ranking.rating_threshold),
        threshold_source=ranking.threshold_source,
        market_average_rating=str(ranking.market_average_rating),
        count=len(ranking.sellers),
        sellers=[
            SellerSalesRatingResult(
                seller_id=seller.seller_id,
                total_orders=seller.total_orders,
                total_revenue=str(seller.total_revenue),
                average_rating=str(seller.average_rating),
                total_reviews=seller.total_reviews,
            )
            for seller in ranking.sellers
        ],
    )


if __name__ == "__main__":
    mcp.run()
