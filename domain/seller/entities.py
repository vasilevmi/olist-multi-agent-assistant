"""Сущности продавцов."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Seller:
    """Основная информация о продавце."""

    seller_id: str
    zip_code_prefix: str
    city: str
    state: str

    @property
    def location(self) -> str:
        """Короткое представление местоположения продавца."""
        return f"{self.city}, {self.state}"


@dataclass
class SellerPerformance:
    """Сводные показатели продавца из нескольких доменов."""

    seller_id: str
    total_orders: int
    total_revenue: Decimal
    average_rating: Decimal | None
    average_delivery_days: Decimal | None
    delayed_orders: int


@dataclass
class SellerCatalog:
    """Категории и уникальные товары, которые продавец продавал."""

    seller_id: str
    total_categories: int
    total_unique_products: int
    categories: list[str]
    product_ids: list[str]


@dataclass
class SellerProductSales:
    """Показатели продаж одного товара у конкретного продавца."""

    product_id: str
    category_name: str | None
    total_orders: int
    total_items: int
    total_revenue: Decimal
    average_price: Decimal


@dataclass
class SellerSalesRating:
    """Продажи и клиентский рейтинг одного продавца."""

    seller_id: str
    total_orders: int
    total_revenue: Decimal
    average_rating: Decimal
    total_reviews: int


@dataclass
class SellerSalesRatingRanking:
    """Продавцы с высокой выручкой и рейтингом ниже порога."""

    ranking_metric: str
    candidate_pool_size: int
    evaluated_sellers: int
    rating_threshold: Decimal
    threshold_source: str
    market_average_rating: Decimal
    sellers: list[SellerSalesRating]
