"""MCP-сервер инструментов доставки."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import MCPServer
from pydantic import BaseModel
from sqlalchemy import create_engine

from application.delivery.use_cases import (
    FindSellersByDelayRate,
    GetCategoryDeliveryRanking,
    GetDelayedOrders,
    GetDeliveryByOrderId,
    GetDeliveryByRegion,
    GetDeliveryStatistics,
    GetRegionDeliveryRanking,
    GetSellerDeliveryPerformance,
)
from domain.delivery.entities import Delivery
from infrastructure.postgres.delivery_repository import (
    PostgresDeliveryRepository,
)


class DeliveryResult(BaseModel):
    """Информация о доставке одного заказа."""

    order_id: str
    purchase_date: str
    delivered_date: str | None
    estimated_delivery_date: str | None
    is_delivered: bool
    is_delayed: bool | None
    delivery_days: float | None
    delay_days: float | None


class DeliveryStatisticsResult(BaseModel):
    """Общие показатели доставки."""

    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: str
    delayed_percentage: str
    average_delivery_days: str
    average_delay_days: str


class DelayedOrdersResult(BaseModel):
    """Список самых сильно задержанных заказов."""

    orders: list[DeliveryResult]


class SellerDeliveryPerformanceResult(BaseModel):
    """Показатели доставки конкретного продавца."""

    seller_id: str
    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: str
    delayed_percentage: str
    average_delivery_days: str
    average_delay_days: str


class SellerAverageDeliveryTimeResult(BaseModel):
    """Среднее время доставки заказов продавца."""

    seller_id: str
    total_delivered_orders: int
    average_delivery_days: str


class SellersByDelayRateResult(BaseModel):
    """Продавцы, чья доля задержек выше заданного порога."""

    delay_threshold: str
    delay_threshold_percentage: str
    min_orders: int
    count: int
    start_date: str | None
    end_date: str | None
    sellers: list[SellerDeliveryPerformanceResult]


class RegionDeliveryPerformanceResult(BaseModel):
    """Показатели доставки в регионе покупателей."""

    region: str
    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: str
    delayed_percentage: str
    average_delivery_days: str
    average_delay_days: str


class CategoryDeliveryPerformanceResult(BaseModel):
    """Показатели задержек одной товарной категории."""

    category_name: str
    total_delivered_orders: int
    delayed_orders: int
    delayed_share: str
    delayed_percentage: str
    average_delivery_days: str
    average_delay_days: str


class CategoryDeliveryRankingResult(BaseModel):
    """Рейтинг категорий по проблемам с доставкой."""

    ranking_metric: str
    min_orders: int
    requested_limit: int
    returned_categories: int
    start_date: str | None
    end_date: str | None
    order_counting: str
    categories: list[CategoryDeliveryPerformanceResult]


class RegionDeliveryRankingResult(BaseModel):
    """Рейтинг регионов по проблемам с доставкой."""

    ranking_metric: str
    min_orders: int
    requested_limit: int
    returned_regions: int
    start_date: str | None
    end_date: str | None
    regions: list[RegionDeliveryPerformanceResult]


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
repository = PostgresDeliveryRepository(engine)

get_delivery_use_case = GetDeliveryByOrderId(repository)
get_statistics_use_case = GetDeliveryStatistics(repository)
get_delayed_orders_use_case = GetDelayedOrders(repository)
get_seller_performance_use_case = GetSellerDeliveryPerformance(
    repository
)
find_sellers_by_delay_rate_use_case = FindSellersByDelayRate(repository)
get_delivery_by_region_use_case = GetDeliveryByRegion(repository)
get_category_delivery_ranking_use_case = GetCategoryDeliveryRanking(
    repository
)
get_region_delivery_ranking_use_case = GetRegionDeliveryRanking(repository)

mcp = MCPServer("Delivery MCP")


def _to_delivery_result(delivery: Delivery) -> DeliveryResult:
    """Преобразовать доменную доставку в ответ MCP."""

    return DeliveryResult(
        order_id=delivery.order_id,
        purchase_date=delivery.purchase_date.isoformat(),
        delivered_date=(
            delivery.delivered_date.isoformat()
            if delivery.delivered_date is not None
            else None
        ),
        estimated_delivery_date=(
            delivery.estimated_delivery_date.isoformat()
            if delivery.estimated_delivery_date is not None
            else None
        ),
        is_delivered=delivery.is_delivered,
        is_delayed=delivery.is_delayed,
        delivery_days=delivery.delivery_days,
        delay_days=delivery.delay_days,
    )


@mcp.tool()
def get_delivery_by_order_id(order_id: str) -> DeliveryResult:
    """Получить информацию о доставке заказа."""

    delivery = get_delivery_use_case.execute(order_id)

    if delivery is None:
        raise ValueError(f"Заказ {order_id} не найден")

    return _to_delivery_result(delivery)


@mcp.tool()
def get_delivery_statistics(
    start_date: str | None = None,
    end_date: str | None = None,
) -> DeliveryStatisticsResult:
    """Получить статистику доставки за всё время или период."""

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

    statistics = get_statistics_use_case.execute(
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return DeliveryStatisticsResult(
        total_delivered_orders=(
            statistics.total_delivered_orders
        ),
        delayed_orders=statistics.delayed_orders,
        on_time_orders=statistics.on_time_orders,
        delayed_share=str(statistics.delayed_share),
        delayed_percentage=str(
            statistics.delayed_percentage
        ),
        average_delivery_days=str(
            statistics.average_delivery_days
        ),
        average_delay_days=str(
            statistics.average_delay_days
        ),
    )


@mcp.tool()
def get_delayed_orders(
    limit: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
) -> DelayedOrdersResult:
    """Получить самые сильно задержанные заказы магазина."""

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

    deliveries = get_delayed_orders_use_case.execute(
        limit=limit,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return DelayedOrdersResult(
        orders=[
            _to_delivery_result(delivery)
            for delivery in deliveries
        ]
    )


@mcp.tool()
def get_seller_delivery_performance(
    seller_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellerDeliveryPerformanceResult:
    """Получить показатели доставки конкретного продавца."""

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

    performance = get_seller_performance_use_case.execute(
        seller_id=seller_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    if performance is None:
        raise ValueError(
            f"Доставки продавца {seller_id} не найдены"
        )

    return SellerDeliveryPerformanceResult(
        seller_id=performance.seller_id,
        total_delivered_orders=(
            performance.total_delivered_orders
        ),
        delayed_orders=performance.delayed_orders,
        on_time_orders=performance.on_time_orders,
        delayed_share=str(performance.delayed_share),
        delayed_percentage=str(
            performance.delayed_percentage
        ),
        average_delivery_days=str(
            performance.average_delivery_days
        ),
        average_delay_days=str(
            performance.average_delay_days
        ),
    )


@mcp.tool()
def get_seller_average_delivery_time(
    seller_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellerAverageDeliveryTimeResult:
    """Получить среднее время доставки продавца в днях."""

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

    performance = get_seller_performance_use_case.execute(
        seller_id=seller_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    if performance is None:
        raise ValueError(
            f"Доставки продавца {seller_id} не найдены"
        )

    return SellerAverageDeliveryTimeResult(
        seller_id=performance.seller_id,
        total_delivered_orders=(
            performance.total_delivered_orders
        ),
        average_delivery_days=str(
            performance.average_delivery_days
        ),
    )


@mcp.tool()
def find_sellers_by_delay_rate(
    delay_threshold: float = 0.20,
    min_orders: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellersByDelayRateResult:
    """Найти продавцов с долей задержек выше заданного порога."""

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
        raise ValueError("Даты должны быть в формате YYYY-MM-DD") from error

    sellers = find_sellers_by_delay_rate_use_case.execute(
        delay_threshold=delay_threshold,
        min_orders=min_orders,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return SellersByDelayRateResult(
        delay_threshold=str(delay_threshold),
        delay_threshold_percentage=str(delay_threshold * 100),
        min_orders=min_orders,
        count=len(sellers),
        start_date=start_date,
        end_date=end_date,
        sellers=[
            SellerDeliveryPerformanceResult(
                seller_id=seller.seller_id,
                total_delivered_orders=seller.total_delivered_orders,
                delayed_orders=seller.delayed_orders,
                on_time_orders=seller.on_time_orders,
                delayed_share=str(seller.delayed_share),
                delayed_percentage=str(seller.delayed_percentage),
                average_delivery_days=str(seller.average_delivery_days),
                average_delay_days=str(seller.average_delay_days),
            )
            for seller in sellers
        ],
    )


@mcp.tool()
def get_delivery_by_region(
    region: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> RegionDeliveryPerformanceResult:
    """Получить показатели доставки в штате покупателей."""

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

    performance = get_delivery_by_region_use_case.execute(
        region=region,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    if performance is None:
        raise ValueError(
            f"Доставки в регионе {region} не найдены"
        )

    return RegionDeliveryPerformanceResult(
        region=performance.region,
        total_delivered_orders=(
            performance.total_delivered_orders
        ),
        delayed_orders=performance.delayed_orders,
        on_time_orders=performance.on_time_orders,
        delayed_share=str(performance.delayed_share),
        delayed_percentage=str(
            performance.delayed_percentage
        ),
        average_delivery_days=str(
            performance.average_delivery_days
        ),
        average_delay_days=str(
            performance.average_delay_days
        ),
    )


@mcp.tool()
def get_category_delivery_ranking(
    limit: int = 10,
    min_orders: int = 100,
    ranking_metric: str = "delayed_share",
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategoryDeliveryRankingResult:
    """Получить категории с наибольшей долей или числом задержек."""

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

    categories = get_category_delivery_ranking_use_case.execute(
        limit=limit,
        min_orders=min_orders,
        ranking_metric=ranking_metric,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return CategoryDeliveryRankingResult(
        ranking_metric=ranking_metric,
        min_orders=min_orders,
        requested_limit=limit,
        returned_categories=len(categories),
        start_date=start_date,
        end_date=end_date,
        order_counting=(
            "Каждый заказ учитывается один раз в каждой содержащейся "
            "в нём категории"
        ),
        categories=[
            CategoryDeliveryPerformanceResult(
                category_name=category.category_name,
                total_delivered_orders=(
                    category.total_delivered_orders
                ),
                delayed_orders=category.delayed_orders,
                delayed_share=str(category.delayed_share),
                delayed_percentage=str(
                    category.delayed_percentage
                ),
                average_delivery_days=str(
                    category.average_delivery_days
                ),
                average_delay_days=str(
                    category.average_delay_days
                ),
            )
            for category in categories
        ],
    )


@mcp.tool()
def get_region_delivery_ranking(
    limit: int = 10,
    min_orders: int = 100,
    ranking_metric: str = "delayed_share",
    start_date: str | None = None,
    end_date: str | None = None,
) -> RegionDeliveryRankingResult:
    """Получить рейтинг регионов по задержкам или времени доставки."""

    regions = get_region_delivery_ranking_use_case.execute(
        limit=limit,
        min_orders=min_orders,
        ranking_metric=ranking_metric,
        start_date=(
            datetime.fromisoformat(start_date)
            if start_date is not None
            else None
        ),
        end_date=(
            datetime.fromisoformat(end_date)
            if end_date is not None
            else None
        ),
    )

    return RegionDeliveryRankingResult(
        ranking_metric=ranking_metric,
        min_orders=min_orders,
        requested_limit=limit,
        returned_regions=len(regions),
        start_date=start_date,
        end_date=end_date,
        regions=[
            RegionDeliveryPerformanceResult(
                region=region.region,
                total_delivered_orders=region.total_delivered_orders,
                delayed_orders=region.delayed_orders,
                on_time_orders=region.on_time_orders,
                delayed_share=str(region.delayed_share),
                delayed_percentage=str(region.delayed_percentage),
                average_delivery_days=str(region.average_delivery_days),
                average_delay_days=str(region.average_delay_days),
            )
            for region in regions
        ],
    )


if __name__ == "__main__":
    mcp.run()
