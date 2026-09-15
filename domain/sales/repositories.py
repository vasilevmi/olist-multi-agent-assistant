"""Интерфейсы доступа к данным контекста продаж."""

from abc import ABC, abstractmethod
from datetime import datetime

from domain.sales.entities import (
    CategorySalesSummary,
    Order,
    SalesSummary,
    SellerSalesSummary,
)


class SalesRepository(ABC):
    """Порт, через который приложение получает данные о продажах.

    Доменный слой определяет контракт, но не знает, где находятся данные:
    в PostgreSQL, тестовой памяти или другом хранилище.
    """

    @abstractmethod
    def get_order_by_id(self, order_id: str) -> Order | None:
        """Вернуть заказ с позициями либо None, если заказ не найден."""

    @abstractmethod
    def get_sales_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SalesSummary:
        """Вернуть сводку продаж за указанный полуинтервал [start_date, end_date)."""

    @abstractmethod
    def get_seller_sales(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerSalesSummary | None:
        """Вернуть показатели продаж конкретного продавца за период."""

    @abstractmethod
    def get_sales_by_category(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategorySalesSummary | None:
        """Вернуть показатели категории за всё время или за период."""

    @abstractmethod
    def get_category_sales_ranking(
        self,
        limit: int = 10,
        ranking_metric: str = "total_revenue",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategorySalesSummary]:
        """Вернуть рейтинг категорий по показателям продаж."""

    @abstractmethod
    def get_top_sellers(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Вернуть продавцов с наибольшей выручкой."""

    @abstractmethod
    def compare_sellers(
        self,
        seller_ids: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Вернуть показатели выбранных продавцов для сравнения."""
