"""Сценарии использования контекста продаж."""

from datetime import datetime

from domain.sales.entities import (
    CategorySalesSummary,
    Order,
    SalesSummary,
    SellerSalesSummary,
)
from domain.sales.repositories import SalesRepository


class GetOrderById:
    """Сценарий получения заказа по его идентификатору."""

    def __init__(self, repository: SalesRepository) -> None:
        # Use case зависит от интерфейса, а не от PostgreSQL.
        self.repository = repository

    def execute(self, order_id: str) -> Order | None:
        """Проверить входные данные и получить заказ."""

        # Удаляем случайные пробелы в начале и конце ID.
        normalized_order_id = order_id.strip()

        # Пустой идентификатор является ошибкой запроса.
        if not normalized_order_id:
            raise ValueError("order_id не должен быть пустым")

        return self.repository.get_order_by_id(normalized_order_id)


class GetSalesSummary:
    """Сценарий получения сводных показателей продаж."""

    def __init__(self, repository: SalesRepository) -> None:
        # Здесь также используется только абстрактный контракт.
        self.repository = repository

    def execute(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SalesSummary:
        """Проверить период и получить сводку продаж."""

        # Конечная дата должна быть позже начальной.
        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_sales_summary(
            start_date=start_date,
            end_date=end_date,
        )
    
class GetSellerSales:
    """Сценарий получения показателей конкретного продавца."""

    def __init__(self, repository: SalesRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerSalesSummary | None:
        """Проверить параметры и получить продажи продавца."""

        normalized_seller_id = seller_id.strip()

        if not normalized_seller_id:
            raise ValueError("seller_id не должен быть пустым")

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_seller_sales(
            seller_id=normalized_seller_id,
            start_date=start_date,
            end_date=end_date,
        )


class GetSalesByCategory:
    """Сценарий получения продаж конкретной категории."""

    def __init__(self, repository: SalesRepository) -> None:
        self.repository = repository

    def execute(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategorySalesSummary | None:
        """Проверить параметры и получить продажи категории."""

        normalized_category_name = category_name.strip().lower()

        if not normalized_category_name:
            raise ValueError(
                "category_name не должен быть пустым"
            )

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_sales_by_category(
            category_name=normalized_category_name,
            start_date=start_date,
            end_date=end_date,
        )


class GetCategorySalesRanking:
    """Сценарий построения рейтинга товарных категорий по продажам."""

    def __init__(self, repository: SalesRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        ranking_metric: str = "total_revenue",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategorySalesSummary]:
        """Проверить параметры и получить рейтинг категорий."""

        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        if ranking_metric not in {
            "total_revenue",
            "total_orders",
            "total_items",
        }:
            raise ValueError(
                "ranking_metric должен быть total_revenue, "
                "total_orders или total_items"
            )
        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError("end_date должна быть позже start_date")

        return self.repository.get_category_sales_ranking(
            limit=limit,
            ranking_metric=ranking_metric,
            start_date=start_date,
            end_date=end_date,
        )


class GetTopSellers:
    """Сценарий получения продавцов с наибольшей выручкой."""

    def __init__(self, repository: SalesRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Проверить параметры и получить лучших продавцов."""

        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_top_sellers(
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )


class CompareSellers:
    """Сценарий сравнения показателей нескольких продавцов."""

    def __init__(self, repository: SalesRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_ids: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Проверить параметры и получить данные для сравнения."""

        normalized_seller_ids = [
            seller_id.strip() for seller_id in seller_ids
        ]

        if any(not seller_id for seller_id in normalized_seller_ids):
            raise ValueError("seller_id не должен быть пустым")

        # Убираем повторяющиеся ID, сохраняя исходный порядок.
        normalized_seller_ids = list(
            dict.fromkeys(normalized_seller_ids)
        )

        if len(normalized_seller_ids) < 2:
            raise ValueError(
                "Для сравнения нужны минимум два продавца"
            )

        if len(normalized_seller_ids) > 20:
            raise ValueError(
                "За один запрос можно сравнить не более 20 продавцов"
            )

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        summaries = self.repository.compare_sellers(
            seller_ids=normalized_seller_ids,
            start_date=start_date,
            end_date=end_date,
        )

        found_seller_ids = {
            summary.seller_id for summary in summaries
        }
        missing_seller_ids = [
            seller_id
            for seller_id in normalized_seller_ids
            if seller_id not in found_seller_ids
        ]

        if missing_seller_ids:
            raise ValueError(
                "Не найдены продажи продавцов: "
                + ", ".join(missing_seller_ids)
            )

        return summaries
