"""MCP-сервер инструментов контекста продаж."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import MCPServer
from pydantic import BaseModel
from sqlalchemy import create_engine

from application.sales.use_cases import (
    CompareSellers,
    GetCategorySalesRanking,
    GetOrderById,
    GetSalesByCategory,
    GetSalesSummary,
    GetSellerSales,
    GetTopSellers,
)
from infrastructure.postgres.sales_repository import (
    PostgresSalesRepository,
)


class SellerSalesResult(BaseModel):
    """Результат работы MCP-инструмента продаж продавца."""

    seller_id: str
    total_orders: int
    total_revenue: str
    average_order_value: str
    total_items: int
    unique_products: int


class OrderItemResult(BaseModel):
    """Одна товарная позиция заказа."""

    order_item_id: int
    product_id: str
    seller_id: str
    price: str
    freight_value: str


class OrderResult(BaseModel):
    """Заказ вместе с товарными позициями."""

    order_id: str
    customer_id: str
    status: str
    purchase_date: str
    items: list[OrderItemResult]


class SalesSummaryResult(BaseModel):
    """Результат общей сводки продаж."""

    total_orders: int
    total_revenue: str
    average_order_value: str
    total_items: int
    unique_products: int


class CategorySalesResult(BaseModel):
    """Результат продаж конкретной категории."""

    category_name: str
    total_orders: int
    total_revenue: str
    average_order_value: str
    total_items: int
    unique_products: int


class CategorySalesRankingResult(BaseModel):
    """Рейтинг товарных категорий по продажам."""

    ranking_metric: str
    requested_limit: int
    returned_categories: int
    start_date: str | None
    end_date: str | None
    currency: str
    revenue_definition: str
    categories: list[CategorySalesResult]


class TopSellersResult(BaseModel):
    """Список продавцов с наибольшей выручкой."""

    sellers: list[SellerSalesResult]


class CompareSellersResult(BaseModel):
    """Результат сравнения выбранных продавцов."""

    sellers: list[SellerSalesResult]


# Находим корень проекта и загружаем настройки PostgreSQL.
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

database_url = (
    f"postgresql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

# Собираем цепочку: PostgreSQL → repository → use case.
engine = create_engine(database_url)
repository = PostgresSalesRepository(engine)
get_order_by_id_use_case = GetOrderById(repository)
get_seller_sales_use_case = GetSellerSales(repository)
get_sales_summary_use_case = GetSalesSummary(repository)
get_sales_by_category_use_case = GetSalesByCategory(repository)
get_category_sales_ranking_use_case = GetCategorySalesRanking(repository)
get_top_sellers_use_case = GetTopSellers(repository)
compare_sellers_use_case = CompareSellers(repository)

# Создаём MCP-сервер.
mcp = MCPServer("Sales MCP")


@mcp.tool()
def get_order_by_id(order_id: str) -> OrderResult:
    """Получить заказ и все входящие в него товарные позиции."""

    order = get_order_by_id_use_case.execute(order_id)
    if order is None:
        raise ValueError(f"Заказ {order_id} не найден")

    return OrderResult(
        order_id=order.order_id,
        customer_id=order.customer_id,
        status=order.status,
        purchase_date=order.purchase_date.isoformat(),
        items=[
            OrderItemResult(
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                seller_id=item.seller_id,
                price=str(item.price),
                freight_value=str(item.freight_value),
            )
            for item in order.items
        ],
    )


@mcp.tool()
def get_seller_sales(
    seller_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellerSalesResult:
    """Получить показатели продавца за всё время или за период."""

    try:
        parsed_start_date = (
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        )

        parsed_end_date = (
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summary = get_seller_sales_use_case.execute(
        seller_id=seller_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    if summary is None:
        raise ValueError(
            f"Продажи продавца {seller_id} не найдены"
        )

    return SellerSalesResult(
        seller_id=summary.seller_id,
        total_orders=summary.total_orders,
        total_revenue=str(summary.total_revenue),
        average_order_value=str(summary.average_order_value),
        total_items=summary.total_items,
        unique_products=summary.unique_products,
    )


@mcp.tool()
def get_sales_summary() -> SalesSummaryResult:
    """Получить общие показатели продаж магазина."""

    summary = get_sales_summary_use_case.execute()

    return SalesSummaryResult(
        total_orders=summary.total_orders,
        total_revenue=str(summary.total_revenue),
        average_order_value=str(summary.average_order_value),
        total_items=summary.total_items,
        unique_products=summary.unique_products,
    )



@mcp.tool()
def get_sales_by_period(
    start_date: str,
    end_date: str,
) -> SalesSummaryResult:
    """Получить показатели продаж за указанный период."""

    try:
        parsed_start_date = datetime.fromisoformat(start_date)
        parsed_end_date = datetime.fromisoformat(end_date)
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summary = get_sales_summary_use_case.execute(
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return SalesSummaryResult(
        total_orders=summary.total_orders,
        total_revenue=str(summary.total_revenue),
        average_order_value=str(summary.average_order_value),
        total_items=summary.total_items,
        unique_products=summary.unique_products,
    )

@mcp.tool()
def get_sales_by_category(
    category_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategorySalesResult:
    """Получить продажи категории за всё время или за период."""

    try:
        parsed_start_date = (
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        )

        parsed_end_date = (
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summary = get_sales_by_category_use_case.execute(
        category_name=category_name,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    if summary is None:
        raise ValueError(
            f"Продажи категории {category_name} не найдены"
        )

    return CategorySalesResult(
        category_name=summary.category_name,
        total_orders=summary.total_orders,
        total_revenue=str(summary.total_revenue),
        average_order_value=str(
            summary.average_order_value
        ),
        total_items=summary.total_items,
        unique_products=summary.unique_products,
    )


@mcp.tool()
def get_category_sales_ranking(
    limit: int = 10,
    ranking_metric: str = "total_revenue",
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategorySalesRankingResult:
    """Получить рейтинг товарных категорий по показателям продаж."""

    try:
        parsed_start_date = (
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        )
        parsed_end_date = (
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summaries = get_category_sales_ranking_use_case.execute(
        limit=limit,
        ranking_metric=ranking_metric,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return CategorySalesRankingResult(
        ranking_metric=ranking_metric,
        requested_limit=limit,
        returned_categories=len(summaries),
        start_date=start_date,
        end_date=end_date,
        currency="BRL",
        revenue_definition=(
            "Сумма price товарных позиций в доставленных заказах; "
            "freight_value не включён"
        ),
        categories=[
            CategorySalesResult(
                category_name=summary.category_name,
                total_orders=summary.total_orders,
                total_revenue=str(summary.total_revenue),
                average_order_value=str(summary.average_order_value),
                total_items=summary.total_items,
                unique_products=summary.unique_products,
            )
            for summary in summaries
        ],
    )


@mcp.tool()
def get_top_sellers(
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
) -> TopSellersResult:
    """Получить продавцов с наибольшей выручкой."""

    try:
        parsed_start_date = (
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        )

        parsed_end_date = (
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summaries = get_top_sellers_use_case.execute(
        limit=limit,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return TopSellersResult(
        sellers=[
            SellerSalesResult(
                seller_id=summary.seller_id,
                total_orders=summary.total_orders,
                total_revenue=str(summary.total_revenue),
                average_order_value=str(
                    summary.average_order_value
                ),
                total_items=summary.total_items,
                unique_products=summary.unique_products,
            )
            for summary in summaries
        ]
    )


@mcp.tool()
def compare_sellers(
    seller_ids: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> CompareSellersResult:
    """Сравнить продажи нескольких продавцов."""

    try:
        parsed_start_date = (
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        )

        parsed_end_date = (
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        )
    except ValueError as error:
        raise ValueError(
            "Даты должны быть в формате YYYY-MM-DD"
        ) from error

    summaries = compare_sellers_use_case.execute(
        seller_ids=seller_ids,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return CompareSellersResult(
        sellers=[
            SellerSalesResult(
                seller_id=summary.seller_id,
                total_orders=summary.total_orders,
                total_revenue=str(summary.total_revenue),
                average_order_value=str(
                    summary.average_order_value
                ),
                total_items=summary.total_items,
                unique_products=summary.unique_products,
            )
            for summary in summaries
        ]
    )

if __name__ == "__main__":
    mcp.run()
