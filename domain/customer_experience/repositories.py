"""Интерфейс доступа к данным об отзывах."""

from abc import ABC, abstractmethod
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


class ReviewRepository(ABC):
    """Договор получения данных о клиентских отзывах."""

    @abstractmethod
    def get_review_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ReviewStatistics:
        """Вернуть общую статистику отзывов за период."""

    @abstractmethod
    def get_seller_rating(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerRatingSummary | None:
        """Вернуть статистику отзывов заказов продавца."""

    @abstractmethod
    def get_category_rating(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategoryRatingSummary | None:
        """Вернуть статистику отзывов заказов категории."""

    @abstractmethod
    def get_category_rating_ranking(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryRatingRankItem]:
        """Вернуть категории с самой высокой средней оценкой."""

    @abstractmethod
    def get_category_negative_review_ranking(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryNegativeReviewRankItem]:
        """Вернуть категории с наибольшей долей негативных отзывов."""

    @abstractmethod
    def get_product_review_summary(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductReviewSummary | None:
        """Вернуть статистику отзывов заказов с товаром."""

    @abstractmethod
    def get_negative_reviews(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        """Вернуть последние негативные отзывы."""

    @abstractmethod
    def get_seller_negative_reviews(
        self,
        seller_id: str,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        """Вернуть негативные отзывы заказов конкретного продавца."""

    @abstractmethod
    def get_rating_distribution(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RatingDistribution:
        """Вернуть распределение оценок от 1 до 5."""

    @abstractmethod
    def analyze_delivery_rating_relationship(
        self,
        seller_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryRatingRelationship:
        """Сравнить оценки своевременных и задержанных доставок."""
