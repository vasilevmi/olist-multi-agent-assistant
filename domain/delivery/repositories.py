"""Интерфейс доступа к данным о доставке."""

from abc import ABC, abstractmethod
from datetime import datetime

from domain.delivery.entities import (
    CategoryDeliveryPerformance,
    Delivery,
    DeliveryStatistics,
    RegionDeliveryPerformance,
    SellerDeliveryPerformance,
)


class DeliveryRepository(ABC):
    """Договор получения данных о доставке."""

    @abstractmethod
    def get_delivery_by_order_id(
        self,
        order_id: str,
    ) -> Delivery | None:
        """Вернуть информацию о доставке одного заказа."""

    @abstractmethod
    def get_delivery_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryStatistics:
        """Вернуть общую статистику доставки за период."""

    @abstractmethod
    def get_delayed_orders(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Delivery]:
        """Вернуть самые сильно задержанные заказы."""

    @abstractmethod
    def get_seller_delivery_performance(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerDeliveryPerformance | None:
        """Вернуть показатели доставки конкретного продавца."""

    @abstractmethod
    def find_sellers_by_delay_rate(
        self,
        delay_threshold: float = 0.20,
        min_orders: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerDeliveryPerformance]:
        """Вернуть продавцов с долей задержек выше заданного порога."""

    @abstractmethod
    def get_delivery_by_region(
        self,
        region: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RegionDeliveryPerformance | None:
        """Вернуть показатели доставки в регионе покупателей."""

    @abstractmethod
    def get_region_delivery_ranking(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RegionDeliveryPerformance]:
        """Вернуть регионы с наибольшими проблемами доставки."""

    @abstractmethod
    def get_category_delivery_ranking(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryDeliveryPerformance]:
        """Вернуть категории с наибольшими проблемами доставки."""
