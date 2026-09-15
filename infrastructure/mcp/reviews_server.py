"""MCP-сервер инструментов отзывов и клиентского опыта."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import MCPServer
from pydantic import BaseModel
from sqlalchemy import create_engine

from application.customer_experience.use_cases import (
    AnalyzeDeliveryRatingRelationship,
    GetCategoryNegativeReviewRanking,
    GetCategoryRating,
    GetCategoryRatingRanking,
    GetNegativeReviews,
    GetProductReviewSummary,
    GetRatingDistribution,
    GetReviewStatistics,
    GetSellerRating,
    GetSellerNegativeReviews,
)
from domain.customer_experience.entities import ReviewStatistics
from infrastructure.postgres.review_repository import PostgresReviewRepository


class ReviewStatisticsResult(BaseModel):
    """Общие показатели клиентских отзывов."""

    total_reviews: int
    average_score: str
    negative_reviews: int
    neutral_reviews: int
    positive_reviews: int
    negative_share: str
    negative_percentage: str
    positive_share: str
    positive_percentage: str


class SellerScoreDistributionResult(BaseModel):
    """Точное количество оценок продавца от 1 до 5."""

    total_reviews: int
    score_1: int
    score_2: int
    score_3: int
    score_4: int
    score_5: int


class SellerRatingResult(BaseModel):
    """Оценки заказов, в которых есть товары продавца."""

    seller_id: str
    attribution_scope: str
    statistics: ReviewStatisticsResult
    rating_distribution: SellerScoreDistributionResult


class CategoryRatingResult(BaseModel):
    """Оценки заказов, в которых есть товары категории."""

    category_name: str
    attribution_scope: str
    statistics: ReviewStatisticsResult


class CategoryRatingRankItemResult(BaseModel):
    """Одна категория в рейтинге клиентских оценок."""

    category_name: str
    total_reviews: int
    average_score: str


class CategoryRatingRankingResult(BaseModel):
    """Категории с наиболее высокой средней оценкой."""

    requested_limit: int
    min_reviews: int
    returned_categories: int
    start_date: str | None
    end_date: str | None
    attribution_scope: str
    categories: list[CategoryRatingRankItemResult]


class CategoryNegativeReviewRankItemResult(BaseModel):
    """Одна категория в рейтинге негативных отзывов."""

    category_name: str
    total_reviews: int
    negative_reviews: int
    negative_share: str
    negative_percentage: str
    average_score: str


class CategoryNegativeReviewRankingResult(BaseModel):
    """Категории с наибольшей долей оценок 1 и 2."""

    requested_limit: int
    min_reviews: int
    returned_categories: int
    start_date: str | None
    end_date: str | None
    negative_review_definition: str
    attribution_scope: str
    categories: list[CategoryNegativeReviewRankItemResult]


class ProductReviewSummaryResult(BaseModel):
    """Оценки заказов, в которых есть выбранный товар."""

    product_id: str
    attribution_scope: str
    statistics: ReviewStatisticsResult


class ReviewResult(BaseModel):
    """Один негативный отзыв."""

    review_id: str
    order_id: str
    score: int
    comment_title: str | None
    comment_message: str | None
    creation_date: str
    answer_timestamp: str | None


class NegativeReviewsResult(BaseModel):
    """Список последних негативных отзывов."""

    count: int
    reviews: list[ReviewResult]


class SellerNegativeReviewsResult(BaseModel):
    """Негативные отзывы заказов конкретного продавца."""

    seller_id: str
    attribution_scope: str
    requested_limit: int
    count: int
    reviews: list[ReviewResult]


class RatingDistributionResult(BaseModel):
    """Количество отзывов с каждой оценкой."""

    total_reviews: int
    score_1: int
    score_2: int
    score_3: int
    score_4: int
    score_5: int


class DeliveryRatingRelationshipResult(BaseModel):
    """Сравнение клиентских оценок по соблюдению срока доставки."""

    unit_of_analysis: str
    seller_id: str | None
    analysis_scope: str
    total_reviews: int
    delayed_reviews: int
    on_time_reviews: int
    delayed_average_score: str
    on_time_average_score: str
    average_score_difference: str
    delayed_negative_share: str
    delayed_negative_percentage: str
    on_time_negative_share: str
    on_time_negative_percentage: str
    delay_status_score_correlation: str | None
    delay_days_score_correlation: str | None
    interpretation_note: str


def _parse_date(value: str | None) -> datetime | None:
    """Преобразовать дату из MCP-запроса в datetime."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Дата должна быть в формате YYYY-MM-DD") from error


def _to_statistics_result(
    statistics: ReviewStatistics,
) -> ReviewStatisticsResult:
    """Преобразовать доменную сущность в ответ MCP."""
    return ReviewStatisticsResult(
        total_reviews=statistics.total_reviews,
        average_score=str(statistics.average_score),
        negative_reviews=statistics.negative_reviews,
        neutral_reviews=statistics.neutral_reviews,
        positive_reviews=statistics.positive_reviews,
        negative_share=str(statistics.negative_share),
        negative_percentage=str(statistics.negative_percentage),
        positive_share=str(statistics.positive_share),
        positive_percentage=str(statistics.positive_percentage),
    )


project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

database_url = (
    f"postgresql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(database_url)
repository = PostgresReviewRepository(engine)
get_review_statistics_use_case = GetReviewStatistics(repository)
get_seller_rating_use_case = GetSellerRating(repository)
get_category_rating_use_case = GetCategoryRating(repository)
get_category_rating_ranking_use_case = GetCategoryRatingRanking(repository)
get_category_negative_review_ranking_use_case = (
    GetCategoryNegativeReviewRanking(repository)
)
get_product_review_summary_use_case = GetProductReviewSummary(repository)
get_negative_reviews_use_case = GetNegativeReviews(repository)
get_seller_negative_reviews_use_case = GetSellerNegativeReviews(repository)
get_rating_distribution_use_case = GetRatingDistribution(repository)
analyze_delivery_rating_use_case = AnalyzeDeliveryRatingRelationship(
    repository
)

mcp = MCPServer("Reviews MCP")


@mcp.tool()
def get_review_statistics(
    start_date: str | None = None,
    end_date: str | None = None,
) -> ReviewStatisticsResult:
    """Получить общую статистику отзывов за период."""
    statistics = get_review_statistics_use_case.execute(
        _parse_date(start_date),
        _parse_date(end_date),
    )
    return _to_statistics_result(statistics)


@mcp.tool()
def get_seller_rating(
    seller_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellerRatingResult:
    """Получить рейтинг заказов конкретного продавца."""
    summary = get_seller_rating_use_case.execute(
        seller_id,
        _parse_date(start_date),
        _parse_date(end_date),
    )
    if summary is None:
        raise ValueError(f"Отзывы продавца {seller_id} не найдены")
    return SellerRatingResult(
        seller_id=summary.seller_id,
        attribution_scope=summary.attribution_scope,
        statistics=_to_statistics_result(summary.statistics),
        rating_distribution=SellerScoreDistributionResult(
            total_reviews=summary.distribution.total_reviews,
            score_1=summary.distribution.score_1,
            score_2=summary.distribution.score_2,
            score_3=summary.distribution.score_3,
            score_4=summary.distribution.score_4,
            score_5=summary.distribution.score_5,
        ),
    )


@mcp.tool()
def get_category_rating(
    category_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategoryRatingResult:
    """Получить рейтинг заказов с товарами выбранной категории."""
    summary = get_category_rating_use_case.execute(
        category_name,
        _parse_date(start_date),
        _parse_date(end_date),
    )
    if summary is None:
        raise ValueError(f"Отзывы категории {category_name} не найдены")
    return CategoryRatingResult(
        category_name=summary.category_name,
        attribution_scope=summary.attribution_scope,
        statistics=_to_statistics_result(summary.statistics),
    )


@mcp.tool()
def get_category_rating_ranking(
    limit: int = 10,
    min_reviews: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategoryRatingRankingResult:
    """Получить категории с самой высокой средней оценкой."""

    parsed_start_date = _parse_date(start_date)
    parsed_end_date = _parse_date(end_date)
    categories = get_category_rating_ranking_use_case.execute(
        limit=limit,
        min_reviews=min_reviews,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )

    return CategoryRatingRankingResult(
        requested_limit=limit,
        min_reviews=min_reviews,
        returned_categories=len(categories),
        start_date=start_date,
        end_date=end_date,
        attribution_scope="order_contains_category",
        categories=[
            CategoryRatingRankItemResult(
                category_name=category.category_name,
                total_reviews=category.total_reviews,
                average_score=str(category.average_score),
            )
            for category in categories
        ],
    )


@mcp.tool()
def get_category_negative_review_ranking(
    limit: int = 10,
    min_reviews: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CategoryNegativeReviewRankingResult:
    """Получить категории с наибольшей долей оценок 1 и 2."""

    categories = get_category_negative_review_ranking_use_case.execute(
        limit=limit,
        min_reviews=min_reviews,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )

    return CategoryNegativeReviewRankingResult(
        requested_limit=limit,
        min_reviews=min_reviews,
        returned_categories=len(categories),
        start_date=start_date,
        end_date=end_date,
        negative_review_definition="review_score <= 2",
        attribution_scope="order_contains_category",
        categories=[
            CategoryNegativeReviewRankItemResult(
                category_name=category.category_name,
                total_reviews=category.total_reviews,
                negative_reviews=category.negative_reviews,
                negative_share=str(category.negative_share),
                negative_percentage=str(category.negative_percentage),
                average_score=str(category.average_score),
            )
            for category in categories
        ],
    )


@mcp.tool()
def get_product_review_summary(
    product_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ProductReviewSummaryResult:
    """Получить сводку отзывов заказов с конкретным товаром."""
    summary = get_product_review_summary_use_case.execute(
        product_id,
        _parse_date(start_date),
        _parse_date(end_date),
    )
    if summary is None:
        raise ValueError(f"Отзывы товара {product_id} не найдены")
    return ProductReviewSummaryResult(
        product_id=summary.product_id,
        attribution_scope=summary.attribution_scope,
        statistics=_to_statistics_result(summary.statistics),
    )


@mcp.tool()
def get_negative_reviews(
    limit: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
) -> NegativeReviewsResult:
    """Получить последние негативные отзывы с оценками 1 и 2."""
    reviews = get_negative_reviews_use_case.execute(
        limit,
        _parse_date(start_date),
        _parse_date(end_date),
    )
    return NegativeReviewsResult(
        count=len(reviews),
        reviews=[
            ReviewResult(
                review_id=review.review_id,
                order_id=review.order_id,
                score=review.score,
                comment_title=review.comment_title,
                comment_message=review.comment_message,
                creation_date=review.creation_date.isoformat(),
                answer_timestamp=(
                    review.answer_timestamp.isoformat()
                    if review.answer_timestamp is not None
                    else None
                ),
            )
            for review in reviews
        ],
    )


@mcp.tool()
def get_seller_negative_reviews(
    seller_id: str,
    limit: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SellerNegativeReviewsResult:
    """Получить негативные отзывы заказов конкретного продавца."""

    reviews = get_seller_negative_reviews_use_case.execute(
        seller_id,
        limit,
        _parse_date(start_date),
        _parse_date(end_date),
    )

    return SellerNegativeReviewsResult(
        seller_id=seller_id.strip(),
        attribution_scope="order_contains_seller",
        requested_limit=limit,
        count=len(reviews),
        reviews=[
            ReviewResult(
                review_id=review.review_id,
                order_id=review.order_id,
                score=review.score,
                comment_title=review.comment_title,
                comment_message=review.comment_message,
                creation_date=review.creation_date.isoformat(),
                answer_timestamp=(
                    review.answer_timestamp.isoformat()
                    if review.answer_timestamp is not None
                    else None
                ),
            )
            for review in reviews
        ],
    )


@mcp.tool()
def get_rating_distribution(
    start_date: str | None = None,
    end_date: str | None = None,
) -> RatingDistributionResult:
    """Получить распределение клиентских оценок от 1 до 5."""
    distribution = get_rating_distribution_use_case.execute(
        _parse_date(start_date),
        _parse_date(end_date),
    )
    return RatingDistributionResult(
        total_reviews=distribution.total_reviews,
        score_1=distribution.score_1,
        score_2=distribution.score_2,
        score_3=distribution.score_3,
        score_4=distribution.score_4,
        score_5=distribution.score_5,
    )


@mcp.tool()
def analyze_delivery_rating_relationship(
    seller_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> DeliveryRatingRelationshipResult:
    """Проанализировать связь задержки доставки с оценкой клиента."""

    relationship = analyze_delivery_rating_use_case.execute(
        seller_id,
        _parse_date(start_date),
        _parse_date(end_date),
    )

    return DeliveryRatingRelationshipResult(
        unit_of_analysis="review_linked_to_delivered_order",
        seller_id=relationship.seller_id,
        analysis_scope=(
            "seller_orders"
            if relationship.seller_id is not None
            else "all_store_orders"
        ),
        total_reviews=relationship.total_reviews,
        delayed_reviews=relationship.delayed_reviews,
        on_time_reviews=relationship.on_time_reviews,
        delayed_average_score=str(
            relationship.delayed_average_score
        ),
        on_time_average_score=str(
            relationship.on_time_average_score
        ),
        average_score_difference=str(
            relationship.average_score_difference
        ),
        delayed_negative_share=str(
            relationship.delayed_negative_share
        ),
        delayed_negative_percentage=str(
            relationship.delayed_negative_percentage
        ),
        on_time_negative_share=str(
            relationship.on_time_negative_share
        ),
        on_time_negative_percentage=str(
            relationship.on_time_negative_percentage
        ),
        delay_status_score_correlation=(
            str(relationship.delay_status_score_correlation)
            if relationship.delay_status_score_correlation is not None
            else None
        ),
        delay_days_score_correlation=(
            str(relationship.delay_days_score_correlation)
            if relationship.delay_days_score_correlation is not None
            else None
        ),
        interpretation_note=(
            "Корреляция показывает статистическую связь, "
            "но сама по себе не доказывает причинность"
        ),
    )


if __name__ == "__main__":
    mcp.run()
