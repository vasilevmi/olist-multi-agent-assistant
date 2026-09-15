"""Интерфейс доступа к данным каталога."""

from abc import ABC, abstractmethod
from datetime import datetime

from domain.catalog.entities import Category, Product, ProductStatistics


class CatalogRepository(ABC):
    """Договор получения товаров и категорий из хранилища."""

    @abstractmethod
    def get_product(self, product_id: str) -> Product | None:
        """Вернуть товар либо None, если он не найден."""

    @abstractmethod
    def get_category(self, category_name: str) -> Category | None:
        """Вернуть категорию и количество товаров в ней."""

    @abstractmethod
    def get_category_products(
        self,
        category_name: str,
        limit: int = 20,
    ) -> list[Product]:
        """Вернуть товары выбранной категории."""

    @abstractmethod
    def get_product_statistics(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductStatistics | None:
        """Вернуть показатели продаж товара за период."""
