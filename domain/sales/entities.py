"""
Сущности контекста "Продажи" (Sales)

Этот модуль содержит бизнес-сущности, связанные с продажами в интернет-магазине.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class OrderItem:
    """Позиция заказа, приобретённая у конкретного продавца."""

    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    price: Decimal
    freight_value: Decimal

    def __post_init__(self) -> None:
        if self.order_item_id <= 0:
            raise ValueError("order_item_id должен быть положительным")
        if self.price < 0:
            raise ValueError("Цена товара не может быть отрицательной")
        if self.freight_value < 0:
            raise ValueError("Стоимость доставки не может быть отрицательной")

    @property
    def total_amount(self) -> Decimal:
        """Полная стоимость позиции: товар плюс доставка."""
        return self.price + self.freight_value


@dataclass
class Order:
    """Заказ — корневая сущность агрегата продаж."""

    order_id: str
    customer_id: str
    status: str
    purchase_date: datetime
    items: list[OrderItem] = field(default_factory=list)

    @property
    def total_amount(self) -> Decimal:
        """Полная сумма заказа с учётом доставки."""
        return sum(
            (item.total_amount for item in self.items),
            start=Decimal("0.00"),
        )

    @property
    def is_delivered(self) -> bool:
        """Имеет ли заказ статус доставки."""
        return self.status == "delivered"

    @property
    def has_items(self) -> bool:
        """Есть ли в заказе хотя бы одна позиция."""
        return bool(self.items)

    @property
    def unique_sellers(self) -> list[str]:
        """Уникальные идентификаторы продавцов в стабильном порядке."""
        return sorted({item.seller_id for item in self.items})

    @property
    def item_count(self) -> int:
        """Количество позиций в заказе."""
        return len(self.items)


@dataclass
class SalesSummary:
    """Сводные показатели продаж по магазину."""

    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    total_items: int
    unique_products: int

    @property
    def formatted_revenue(self) -> str:
        """Выручка, отформатированная в бразильских реалах."""
        return f"R${self.total_revenue:,.2f}"

    @property
    def formatted_average_order(self) -> str:
        """Средний чек, отформатированный в бразильских реалах."""
        return f"R${self.average_order_value:,.2f}"

@dataclass
class SellerSalesSummary:
    """Сводные показатели продаж конкретного продавца."""

    seller_id: str
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    total_items: int
    unique_products: int

    @property
    def formatted_revenue(self) -> str:
        """Выручка продавца в удобном формате."""
        return f"R${self.total_revenue:,.2f}"

    @property
    def formatted_average_order(self) -> str:
        """Средняя сумма продаж продавца на один заказ."""
        return f"R${self.average_order_value:,.2f}"

@dataclass
class CategorySalesSummary:
    """Показатели продаж конкретной категории товаров."""

    category_name: str
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    total_items: int
    unique_products: int

    @property
    def formatted_revenue(self) -> str:
        """Выручка категории в удобном формате."""
        return f"R${self.total_revenue:,.2f}"

    @property
    def formatted_average_order(self) -> str:
        """Средняя выручка категории на один заказ."""
        return f"R${self.average_order_value:,.2f}"