"""Сущности отзывов и клиентского опыта."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Review:
    """Отзыв клиента о заказе."""

    review_id: str
    order_id: str
    score: int
    comment_title: str | None
    comment_message: str | None
    creation_date: datetime
    answer_timestamp: datetime | None

    def __post_init__(self) -> None:
        if self.score < 1 or self.score > 5:
            raise ValueError("Оценка должна быть от 1 до 5")

    @property
    def is_negative(self) -> bool:
        """Является ли отзыв негативным."""
        return self.score <= 2

    @property
    def is_neutral(self) -> bool:
        """Является ли отзыв нейтральным."""
        return self.score == 3

    @property
    def is_positive(self) -> bool:
        """Является ли отзыв положительным."""
        return self.score >= 4


@dataclass
class ReviewStatistics:
    """Общие показатели клиентских оценок."""

    total_reviews: int
    average_score: Decimal
    negative_reviews: int
    neutral_reviews: int
    positive_reviews: int
    negative_share: Decimal
    positive_share: Decimal

    @property
    def negative_percentage(self) -> Decimal:
        """Процент негативных отзывов."""
        return self.negative_share * Decimal("100")

    @property
    def positive_percentage(self) -> Decimal:
        """Процент положительных отзывов."""
        return self.positive_share * Decimal("100")


@dataclass
class RatingDistribution:
    """Распределение клиентских оценок от 1 до 5."""

    total_reviews: int
    score_1: int
    score_2: int
    score_3: int
    score_4: int
    score_5: int


@dataclass
class SellerRatingSummary:
    """Статистика отзывов заказов конкретного продавца."""

    seller_id: str
    statistics: ReviewStatistics
    distribution: RatingDistribution
    attribution_scope: str = "order_contains_seller"


@dataclass
class CategoryRatingSummary:
    """Статистика отзывов заказов конкретной категории."""

    category_name: str
    statistics: ReviewStatistics
    attribution_scope: str = "order_contains_category"


@dataclass
class CategoryRatingRankItem:
    """Одна категория в рейтинге по средней клиентской оценке."""

    category_name: str
    total_reviews: int
    average_score: Decimal


@dataclass
class CategoryNegativeReviewRankItem:
    """Одна категория в рейтинге по доле негативных отзывов."""

    category_name: str
    total_reviews: int
    negative_reviews: int
    negative_share: Decimal
    average_score: Decimal

    @property
    def negative_percentage(self) -> Decimal:
        """Доля негативных отзывов в процентах."""
        return self.negative_share * Decimal("100")


@dataclass
class ProductReviewSummary:
    """Статистика отзывов заказов с конкретным товаром."""

    product_id: str
    statistics: ReviewStatistics
    attribution_scope: str = "order_contains_product"


@dataclass
class DeliveryRatingRelationship:
    """Связь соблюдения срока доставки с клиентской оценкой."""

    seller_id: str | None
    total_reviews: int
    delayed_reviews: int
    on_time_reviews: int
    delayed_average_score: Decimal
    on_time_average_score: Decimal
    delayed_negative_share: Decimal
    on_time_negative_share: Decimal
    delay_status_score_correlation: Decimal | None
    delay_days_score_correlation: Decimal | None

    @property
    def average_score_difference(self) -> Decimal:
        """Насколько оценка своевременных доставок выше задержанных."""
        return self.on_time_average_score - self.delayed_average_score

    @property
    def delayed_negative_percentage(self) -> Decimal:
        return self.delayed_negative_share * Decimal("100")

    @property
    def on_time_negative_percentage(self) -> Decimal:
        return self.on_time_negative_share * Decimal("100")
