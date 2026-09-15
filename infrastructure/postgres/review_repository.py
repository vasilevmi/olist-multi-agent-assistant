"""PostgreSQL-реализация репозитория отзывов."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

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


class PostgresReviewRepository(ReviewRepository):
    """Получает данные об отзывах из PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _statistics_from_row(row: Any) -> ReviewStatistics:
        """Преобразовать строку результата SQL в доменную сущность."""
        return ReviewStatistics(
            total_reviews=int(row["total_reviews"]),
            average_score=Decimal(str(row["average_score"])),
            negative_reviews=int(row["negative_reviews"]),
            neutral_reviews=int(row["neutral_reviews"]),
            positive_reviews=int(row["positive_reviews"]),
            negative_share=Decimal(str(row["negative_share"])),
            positive_share=Decimal(str(row["positive_share"])),
        )

    @staticmethod
    def _statistics_sql(source_sql: str) -> str:
        """Добавить одинаковый расчет показателей к выбранному набору отзывов."""
        return f"""
            {source_sql}
            SELECT
                COUNT(*)::integer AS total_reviews,
                COALESCE(AVG(review_score), 0)::numeric AS average_score,
                COUNT(*) FILTER (WHERE review_score <= 2)::integer
                    AS negative_reviews,
                COUNT(*) FILTER (WHERE review_score = 3)::integer
                    AS neutral_reviews,
                COUNT(*) FILTER (WHERE review_score >= 4)::integer
                    AS positive_reviews,
                COALESCE(
                    COUNT(*) FILTER (WHERE review_score <= 2)::numeric
                    / NULLIF(COUNT(*), 0), 0
                )::numeric AS negative_share,
                COALESCE(
                    COUNT(*) FILTER (WHERE review_score >= 4)::numeric
                    / NULLIF(COUNT(*), 0), 0
                )::numeric AS positive_share
            FROM selected_reviews
            """

    def _execute_statistics(
        self,
        source_sql: str,
        parameters: dict[str, Any],
    ) -> ReviewStatistics:
        """Выполнить SQL и вернуть готовую статистику."""
        with self.engine.connect() as connection:
            row = connection.execute(
                text(self._statistics_sql(source_sql)),
                parameters,
            ).mappings().one()
        return self._statistics_from_row(row)

    def _execute_distribution(
        self,
        source_sql: str,
        parameters: dict[str, Any],
    ) -> RatingDistribution:
        """Посчитать точное распределение оценок выбранного набора отзывов."""

        distribution_sql = f"""
            {source_sql}
            SELECT
                COUNT(*)::integer AS total_reviews,
                COUNT(*) FILTER (WHERE review_score = 1)::integer AS score_1,
                COUNT(*) FILTER (WHERE review_score = 2)::integer AS score_2,
                COUNT(*) FILTER (WHERE review_score = 3)::integer AS score_3,
                COUNT(*) FILTER (WHERE review_score = 4)::integer AS score_4,
                COUNT(*) FILTER (WHERE review_score = 5)::integer AS score_5
            FROM selected_reviews
        """
        with self.engine.connect() as connection:
            row = connection.execute(
                text(distribution_sql),
                parameters,
            ).mappings().one()

        return RatingDistribution(
            total_reviews=int(row["total_reviews"]),
            score_1=int(row["score_1"]),
            score_2=int(row["score_2"]),
            score_3=int(row["score_3"]),
            score_4=int(row["score_4"]),
            score_5=int(row["score_5"]),
        )

    def get_review_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ReviewStatistics:
        """Получить общую статистику отзывов за период."""
        source_sql = """
            WITH selected_reviews AS (
                SELECT review_score
                FROM raw.raw_reviews
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
        """
        return self._execute_statistics(
            source_sql,
            {"start_date": start_date, "end_date": end_date},
        )

    def get_seller_rating(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerRatingSummary | None:
        """Получить статистику отзывов заказов продавца."""
        source_sql = """
            WITH relevant_orders AS (
                SELECT DISTINCT order_id
                FROM raw.raw_order_items
                WHERE seller_id = :seller_id
            ),
            selected_reviews AS (
                SELECT reviews.review_score
                FROM relevant_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = relevant_orders.order_id
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR reviews.review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR reviews.review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
        """
        parameters = {
            "seller_id": seller_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        statistics = self._execute_statistics(source_sql, parameters)
        if statistics.total_reviews == 0:
            return None
        distribution = self._execute_distribution(source_sql, parameters)
        return SellerRatingSummary(
            seller_id=seller_id,
            statistics=statistics,
            distribution=distribution,
        )

    def get_category_rating(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategoryRatingSummary | None:
        """Получить статистику отзывов заказов выбранной категории."""
        source_sql = """
            WITH relevant_orders AS (
                SELECT DISTINCT items.order_id
                FROM raw.raw_order_items AS items
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
                WHERE categories.product_category_name_english
                      = :category_name
            ),
            selected_reviews AS (
                SELECT reviews.review_score
                FROM relevant_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = relevant_orders.order_id
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR reviews.review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR reviews.review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
        """
        statistics = self._execute_statistics(
            source_sql,
            {
                "category_name": category_name,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        if statistics.total_reviews == 0:
            return None
        return CategoryRatingSummary(
            category_name=category_name,
            statistics=statistics,
        )

    def get_category_rating_ranking(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryRatingRankItem]:
        """Сгруппировать отзывы по категориям и отсортировать по оценке."""

        query = text(
            """
            WITH category_orders AS (
                SELECT DISTINCT
                    categories.product_category_name_english
                        AS category_name,
                    items.order_id
                FROM raw.raw_order_items AS items
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
            ),
            category_ratings AS (
                SELECT
                    category_orders.category_name,
                    COUNT(*)::integer AS total_reviews,
                    AVG(reviews.review_score::numeric)::numeric
                        AS average_score
                FROM category_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = category_orders.order_id
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR reviews.review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR reviews.review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
                GROUP BY category_orders.category_name
                HAVING COUNT(*) >= :min_reviews
            )
            SELECT category_name, total_reviews, average_score
            FROM category_ratings
            ORDER BY average_score DESC, total_reviews DESC, category_name
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "limit": limit,
                    "min_reviews": min_reviews,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            CategoryRatingRankItem(
                category_name=str(row["category_name"]),
                total_reviews=int(row["total_reviews"]),
                average_score=Decimal(str(row["average_score"])),
            )
            for row in rows
        ]

    def get_category_negative_review_ranking(
        self,
        limit: int = 10,
        min_reviews: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryNegativeReviewRankItem]:
        """Сгруппировать отзывы по категориям и доле оценок 1–2."""

        query = text(
            """
            WITH category_orders AS (
                SELECT DISTINCT
                    categories.product_category_name_english
                        AS category_name,
                    items.order_id
                FROM raw.raw_order_items AS items
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
            ),
            category_reviews AS (
                SELECT
                    category_orders.category_name,
                    COUNT(*)::integer AS total_reviews,
                    COUNT(*) FILTER (
                        WHERE reviews.review_score <= 2
                    )::integer AS negative_reviews,
                    (
                        COUNT(*) FILTER (
                            WHERE reviews.review_score <= 2
                        )::numeric / NULLIF(COUNT(*), 0)
                    )::numeric AS negative_share,
                    AVG(reviews.review_score::numeric)::numeric
                        AS average_score
                FROM category_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = category_orders.order_id
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR reviews.review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR reviews.review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
                GROUP BY category_orders.category_name
                HAVING COUNT(*) >= :min_reviews
            )
            SELECT
                category_name,
                total_reviews,
                negative_reviews,
                negative_share,
                average_score
            FROM category_reviews
            ORDER BY
                negative_share DESC,
                negative_reviews DESC,
                category_name
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "limit": limit,
                    "min_reviews": min_reviews,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            CategoryNegativeReviewRankItem(
                category_name=str(row["category_name"]),
                total_reviews=int(row["total_reviews"]),
                negative_reviews=int(row["negative_reviews"]),
                negative_share=Decimal(str(row["negative_share"])),
                average_score=Decimal(str(row["average_score"])),
            )
            for row in rows
        ]

    def get_product_review_summary(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductReviewSummary | None:
        """Получить статистику отзывов заказов с выбранным товаром."""
        source_sql = """
            WITH relevant_orders AS (
                SELECT DISTINCT order_id
                FROM raw.raw_order_items
                WHERE product_id = :product_id
            ),
            selected_reviews AS (
                SELECT reviews.review_score
                FROM relevant_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = relevant_orders.order_id
                WHERE (
                    CAST(:start_date AS timestamp) IS NULL
                    OR reviews.review_creation_date::timestamp
                       >= CAST(:start_date AS timestamp)
                )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR reviews.review_creation_date::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
        """
        statistics = self._execute_statistics(
            source_sql,
            {
                "product_id": product_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        if statistics.total_reviews == 0:
            return None
        return ProductReviewSummary(
            product_id=product_id,
            statistics=statistics,
        )

    def get_negative_reviews(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        """Получить последние отзывы с оценками 1 и 2."""
        query = text(
            """
            SELECT
                review_id,
                order_id,
                review_score::integer AS score,
                review_comment_title AS comment_title,
                review_comment_message AS comment_message,
                review_creation_date::timestamp AS creation_date,
                review_answer_timestamp::timestamp AS answer_timestamp
            FROM raw.raw_reviews
            WHERE review_score <= 2
              AND (
                  CAST(:start_date AS timestamp) IS NULL
                  OR review_creation_date::timestamp
                     >= CAST(:start_date AS timestamp)
              )
              AND (
                  CAST(:end_date AS timestamp) IS NULL
                  OR review_creation_date::timestamp
                     < CAST(:end_date AS timestamp)
              )
            ORDER BY review_creation_date::timestamp DESC, review_id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "limit": limit,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            Review(
                review_id=str(row["review_id"]),
                order_id=str(row["order_id"]),
                score=int(row["score"]),
                comment_title=row["comment_title"],
                comment_message=row["comment_message"],
                creation_date=row["creation_date"],
                answer_timestamp=row["answer_timestamp"],
            )
            for row in rows
        ]

    def get_seller_negative_reviews(
        self,
        seller_id: str,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Review]:
        """Получить негативные отзывы заказов с товарами продавца."""

        query = text(
            """
            WITH seller_orders AS (
                SELECT DISTINCT order_id
                FROM raw.raw_order_items
                WHERE seller_id = :seller_id
            )
            SELECT
                reviews.review_id,
                reviews.order_id,
                reviews.review_score::integer AS score,
                reviews.review_comment_title AS comment_title,
                reviews.review_comment_message AS comment_message,
                reviews.review_creation_date::timestamp AS creation_date,
                reviews.review_answer_timestamp::timestamp
                    AS answer_timestamp
            FROM seller_orders
            JOIN raw.raw_reviews AS reviews
                ON reviews.order_id = seller_orders.order_id
            WHERE reviews.review_score <= 2
              AND (
                  CAST(:start_date AS timestamp) IS NULL
                  OR reviews.review_creation_date::timestamp
                     >= CAST(:start_date AS timestamp)
              )
              AND (
                  CAST(:end_date AS timestamp) IS NULL
                  OR reviews.review_creation_date::timestamp
                     < CAST(:end_date AS timestamp)
              )
            ORDER BY
                reviews.review_creation_date::timestamp DESC,
                reviews.review_id
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "seller_id": seller_id,
                    "limit": limit,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            Review(
                review_id=str(row["review_id"]),
                order_id=str(row["order_id"]),
                score=int(row["score"]),
                comment_title=row["comment_title"],
                comment_message=row["comment_message"],
                creation_date=row["creation_date"],
                answer_timestamp=row["answer_timestamp"],
            )
            for row in rows
        ]

    def get_rating_distribution(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RatingDistribution:
        """Получить количество оценок каждого значения от 1 до 5."""
        query = text(
            """
            SELECT
                COUNT(*)::integer AS total_reviews,
                COUNT(*) FILTER (WHERE review_score = 1)::integer AS score_1,
                COUNT(*) FILTER (WHERE review_score = 2)::integer AS score_2,
                COUNT(*) FILTER (WHERE review_score = 3)::integer AS score_3,
                COUNT(*) FILTER (WHERE review_score = 4)::integer AS score_4,
                COUNT(*) FILTER (WHERE review_score = 5)::integer AS score_5
            FROM raw.raw_reviews
            WHERE (
                CAST(:start_date AS timestamp) IS NULL
                OR review_creation_date::timestamp
                   >= CAST(:start_date AS timestamp)
            )
              AND (
                  CAST(:end_date AS timestamp) IS NULL
                  OR review_creation_date::timestamp
                     < CAST(:end_date AS timestamp)
              )
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {"start_date": start_date, "end_date": end_date},
            ).mappings().one()

        return RatingDistribution(
            total_reviews=int(row["total_reviews"]),
            score_1=int(row["score_1"]),
            score_2=int(row["score_2"]),
            score_3=int(row["score_3"]),
            score_4=int(row["score_4"]),
            score_5=int(row["score_5"]),
        )

    def analyze_delivery_rating_relationship(
        self,
        seller_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryRatingRelationship:
        """Рассчитать совместные показатели доставок и отзывов."""

        query = text(
            """
            WITH delivery_reviews AS (
                SELECT
                    reviews.review_score::numeric AS score,
                    (
                        orders.order_delivered_customer_date::timestamp
                        > orders.order_estimated_delivery_date::timestamp
                    ) AS is_delayed,
                    GREATEST(
                        EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_estimated_delivery_date::timestamp
                        )) / 86400,
                        0
                    )::numeric AS delay_days
                FROM raw.raw_orders AS orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = orders.order_id
                WHERE orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
                  AND reviews.review_score IS NOT NULL
                  AND (
                      CAST(:seller_id AS text) IS NULL
                      OR EXISTS (
                          SELECT 1
                          FROM raw.raw_order_items AS items
                          WHERE items.order_id = orders.order_id
                            AND items.seller_id
                                = CAST(:seller_id AS text)
                      )
                  )
                  AND (
                      CAST(:start_date AS timestamp) IS NULL
                      OR orders.order_purchase_timestamp::timestamp
                         >= CAST(:start_date AS timestamp)
                  )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR orders.order_purchase_timestamp::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
            SELECT
                COUNT(*)::integer AS total_reviews,
                COUNT(*) FILTER (WHERE is_delayed)::integer
                    AS delayed_reviews,
                COUNT(*) FILTER (WHERE NOT is_delayed)::integer
                    AS on_time_reviews,
                COALESCE(
                    AVG(score) FILTER (WHERE is_delayed), 0
                )::numeric AS delayed_average_score,
                COALESCE(
                    AVG(score) FILTER (WHERE NOT is_delayed), 0
                )::numeric AS on_time_average_score,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE is_delayed AND score <= 2
                    )::numeric
                    / NULLIF(COUNT(*) FILTER (WHERE is_delayed), 0),
                    0
                )::numeric AS delayed_negative_share,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE NOT is_delayed AND score <= 2
                    )::numeric
                    / NULLIF(COUNT(*) FILTER (WHERE NOT is_delayed), 0),
                    0
                )::numeric AS on_time_negative_share,
                CORR(is_delayed::integer, score)::numeric
                    AS delay_status_score_correlation,
                CORR(delay_days, score)::numeric
                    AS delay_days_score_correlation
            FROM delivery_reviews
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {
                    "seller_id": seller_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        return DeliveryRatingRelationship(
            seller_id=seller_id,
            total_reviews=int(row["total_reviews"]),
            delayed_reviews=int(row["delayed_reviews"]),
            on_time_reviews=int(row["on_time_reviews"]),
            delayed_average_score=Decimal(
                str(row["delayed_average_score"])
            ),
            on_time_average_score=Decimal(
                str(row["on_time_average_score"])
            ),
            delayed_negative_share=Decimal(
                str(row["delayed_negative_share"])
            ),
            on_time_negative_share=Decimal(
                str(row["on_time_negative_share"])
            ),
            delay_status_score_correlation=(
                Decimal(str(row["delay_status_score_correlation"]))
                if row["delay_status_score_correlation"] is not None
                else None
            ),
            delay_days_score_correlation=(
                Decimal(str(row["delay_days_score_correlation"]))
                if row["delay_days_score_correlation"] is not None
                else None
            ),
        )
