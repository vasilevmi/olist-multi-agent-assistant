"""Сущности контекста доставки."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Delivery:
    """Информация о доставке одного заказа."""

    order_id: str
    purchase_date: datetime
    delivered_date: datetime | None
    estimated_delivery_date: datetime | None

    @property
    def is_delivered(self) -> bool:
        """Доставлен ли заказ покупателю."""
        return self.delivered_date is not None

    @property
    def is_delayed(self) -> bool | None:
        """Был ли заказ доставлен позже ожидаемой даты."""

        if (
            self.delivered_date is None
            or self.estimated_delivery_date is None
        ):
            return None

        return self.delivered_date > self.estimated_delivery_date

    @property
    def delivery_days(self) -> float | None:
        """Фактическое время доставки в днях."""

        if self.delivered_date is None:
            return None

        difference = self.delivered_date - self.purchase_date
        return difference.total_seconds() / 86400

    @property
    def delay_days(self) -> float | None:
        """Количество дней задержки."""

        if (
            self.delivered_date is None
            or self.estimated_delivery_date is None
        ):
            return None

        if not self.is_delayed:
            return 0.0

        difference = (
            self.delivered_date
            - self.estimated_delivery_date
        )

        return difference.total_seconds() / 86400


@dataclass
class DeliveryStatistics:
    """Общие показатели качества доставки."""

    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: Decimal
    average_delivery_days: Decimal
    average_delay_days: Decimal

    @property
    def delayed_percentage(self) -> Decimal:
        """Доля задержанных заказов в процентах."""
        return self.delayed_share * Decimal("100")


@dataclass
class SellerDeliveryPerformance:
    """Показатели качества доставки конкретного продавца."""

    seller_id: str
    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: Decimal
    average_delivery_days: Decimal
    average_delay_days: Decimal

    @property
    def delayed_percentage(self) -> Decimal:
        """Доля задержанных заказов продавца в процентах."""
        return self.delayed_share * Decimal("100")


@dataclass
class RegionDeliveryPerformance:
    """Показатели качества доставки в регионе покупателей."""

    region: str
    total_delivered_orders: int
    delayed_orders: int
    on_time_orders: int
    delayed_share: Decimal
    average_delivery_days: Decimal
    average_delay_days: Decimal

    @property
    def delayed_percentage(self) -> Decimal:
        """Доля задержанных заказов региона в процентах."""
        return self.delayed_share * Decimal("100")


@dataclass
class CategoryDeliveryPerformance:
    """Показатели доставки заказов, содержащих товары одной категории."""

    category_name: str
    total_delivered_orders: int
    delayed_orders: int
    delayed_share: Decimal
    average_delivery_days: Decimal
    average_delay_days: Decimal

    @property
    def delayed_percentage(self) -> Decimal:
        """Доля задержанных заказов категории в процентах."""
        return self.delayed_share * Decimal("100")
