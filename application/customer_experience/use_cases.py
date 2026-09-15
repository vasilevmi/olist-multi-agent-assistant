"""Сценарии использования отзывов и клиентских оценок."""

from datetime import datetime

from domain.customer_experience.entities import (
    CategoryNegativeReviewRankItem,
    CategoryRatingRankItem,
    CategoryRatingSummary,
    DeliveryRatingRelationship,
    ProductReviewSummary,
    RatingDistribution,
    Review,
    ReviewStatistics,
    SellerRatingSummary,
)
from domain.customer_experience.repositories import ReviewRepository


def _validate_period(
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Проверить, что конец периода находится после начала."""
    if start_date is not None and end_date is not None and end_date <= start_date:
        raise ValueError("end_date должна быть позже start_date")


def _validate_identifier(value: str, field_name: str) -> str:
    """Убрать пробелы и запретить пустой идентификатор."""
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{field_name} не должен быть пустым")
    return cleaned_value


class GetReviewStatistics:
    """Получить общую статистику отзывов."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ReviewStatistics:
        _validate_period(start_date, end_date)
        return self.repository.get_review_statistics(start_date, end_date)


class GetSellerRating:
    """Получить оценки заказов конкретного продавца."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerRatingSummary | None:
        seller_id = _validate_identifier(seller_id, "seller_id")
        _validate_period(start_date, end_date)
        return self.repository.get_seller_rating(seller_id, start_date, end_date)


class GetCategoryRating:
    """Получить оценки заказов выбранной категории."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategoryRatingSummary | None:
        category_name = _validate_identifier(
            category_name,
            "category_name",
        ).lower()
        _validate_period(start_date, end_date)
        return self.repository.get_category_rating(
            category_name,
            start_date,
            end_date,
        )


class GetCategoryRatingRanking:
    """Построить рейтинг категорий по средней оценке клиентов."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryRatingRankItem]:
        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        if min_reviews < 1:
            raise ValueError("min_reviews должен быть положительным")
        _validate_period(start_date, end_date)

        return self.repository.get_category_rating_ranking(
            limit=limit,
            min_reviews=min_reviews,
            start_date=start_date,
            end_date=end_date,
        )


class GetCategoryNegativeReviewRanking:
    """Построить рейтинг категорий по доле оценок 1 и 2."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryNegativeReviewRankItem]:
        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        if min_reviews < 1:
            raise ValueError("min_reviews должен быть положительным")
        _validate_period(start_date, end_date)

        return self.repository.get_category_negative_review_ranking(
            limit=limit,
            min_reviews=min_reviews,
            start_date=start_date,
            end_date=end_date,
        )


class GetProductReviewSummary:
    """Получить оценки заказов с конкретным товаром."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductReviewSummary | None:
        product_id = _validate_identifier(product_id, "product_id")
        _validate_period(start_date, end_date)
        return self.repository.get_product_review_summary(
            product_id,
            start_date,
            end_date,
        )


class GetNegativeReviews:
    """Получить последние негативные отзывы."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")
        _validate_period(start_date, end_date)
        return self.repository.get_negative_reviews(limit, start_date, end_date)


class GetSellerNegativeReviews:
    """Получить последние негативные отзывы заказов продавца."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        seller_id = _validate_identifier(seller_id, "seller_id")
        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        _validate_period(start_date, end_date)
        return self.repository.get_seller_negative_reviews(
            seller_id,
            limit,
            start_date,
            end_date,
        )


class GetRatingDistribution:
    """Получить распределение оценок от 1 до 5."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RatingDistribution:
        _validate_period(start_date, end_date)
        return self.repository.get_rating_distribution(start_date, end_date)


class AnalyzeDeliveryRatingRelationship:
    """Проанализировать связь срока доставки с оценкой клиента."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryRatingRelationship:
        if seller_id is not None:
            seller_id = _validate_identifier(seller_id, "seller_id")
        _validate_period(start_date, end_date)
        return self.repository.analyze_delivery_rating_relationship(
            seller_id,
            start_date,
            end_date,
        )
