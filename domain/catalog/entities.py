"""Сущности каталога товаров."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    """Карточка товара из каталога."""

    product_id: str
    category_name_original: str | None
    category_name_english: str | None
    name_length: int | None
    description_length: int | None
    photos_quantity: int | None
    weight_g: Decimal | None
    length_cm: Decimal | None
    height_cm: Decimal | None
    width_cm: Decimal | None


@dataclass
class Category:
    """Категория и количество относящихся к ней товаров."""

    category_name_original: str
    category_name_english: str
    total_products: int


@dataclass
class ProductStatistics:
    """Показатели продаж конкретного товара."""

    product_id: str
    total_orders: int
    total_items: int
    total_revenue: Decimal
    average_price: Decimal
    unique_sellers: int
