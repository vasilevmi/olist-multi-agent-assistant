"""Сценарии использования каталога товаров."""

from datetime import datetime

from domain.catalog.entities import Category, Product, ProductStatistics
from domain.catalog.repositories import CatalogRepository


def _clean_text(value: str, field_name: str) -> str:
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{field_name} не должен быть пустым")
    return cleaned_value


def _validate_period(
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    if start_date is not None and end_date is not None and end_date <= start_date:
        raise ValueError("end_date должна быть позже start_date")


class GetProduct:
    """Получить карточку конкретного товара."""

    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def execute(self, product_id: str) -> Product | None:
        product_id = _clean_text(product_id, "product_id")
        return self.repository.get_product(product_id)


class GetCategory:
    """Получить сведения о категории."""

    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def execute(self, category_name: str) -> Category | None:
        category_name = _clean_text(category_name, "category_name")
        return self.repository.get_category(category_name)


class GetCategoryProducts:
    """Получить список товаров выбранной категории."""

    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def execute(
        self,
        category_name: str,
        limit: int = 20,
    ) -> list[Product]:
        category_name = _clean_text(category_name, "category_name")
        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")
        return self.repository.get_category_products(category_name, limit)


class GetProductStatistics:
    """Получить показатели завершённых продаж товара."""

    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def execute(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductStatistics | None:
        product_id = _clean_text(product_id, "product_id")
        _validate_period(start_date, end_date)
        return self.repository.get_product_statistics(
            product_id,
            start_date,
            end_date,
        )
