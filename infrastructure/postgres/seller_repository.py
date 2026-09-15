"""PostgreSQL-реализация репозитория продавцов."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from domain.seller.entities import (
    Seller,
    SellerCatalog,
    SellerProductSales,
    SellerSalesRating,
    SellerSalesRatingRanking,
)
from domain.seller.repositories import SellerRepository


class PostgresSellerRepository(SellerRepository):
    """Получает основную информацию о продавцах из PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _seller_from_row(row: Any) -> Seller:
        return Seller(
            seller_id=str(row["seller_id"]),
            zip_code_prefix=str(row["seller_zip_code_prefix"]),
            city=str(row["seller_city"]),
            state=str(row["seller_state"]),
        )

    def get_seller(self, seller_id: str) -> Seller | None:
        """Получить продавца по идентификатору."""
        query = text(
            """
            SELECT
                seller_id,
                seller_zip_code_prefix,
                seller_city,
                seller_state
            FROM raw.raw_sellers
            WHERE seller_id = :seller_id
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {"seller_id": seller_id},
            ).mappings().one_or_none()
        return None if row is None else self._seller_from_row(row)

    def get_sellers_by_location(
        self,
        state: str | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[Seller]:
        """Получить продавцов с необязательным фильтром места."""
        query = text(
            """
            SELECT
                seller_id,
                seller_zip_code_prefix,
                seller_city,
                seller_state
            FROM raw.raw_sellers
            WHERE (
                CAST(:state AS text) IS NULL
                OR UPPER(seller_state) = UPPER(:state)
            )
              AND (
                  CAST(:city AS text) IS NULL
                  OR LOWER(seller_city) = LOWER(:city)
              )
            ORDER BY seller_state, seller_city, seller_id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {"state": state, "city": city, "limit": limit},
            ).mappings().all()
        return [self._seller_from_row(row) for row in rows]

    def get_seller_catalog(
        self,
        seller_id: str,
        product_limit: int = 20,
    ) -> SellerCatalog | None:
        """Получить исторический ассортимент продавца."""
        summary_query = text(
            """
            SELECT
                sellers.seller_id,
                COUNT(DISTINCT items.product_id)::integer
                    AS total_unique_products,
                COUNT(DISTINCT COALESCE(
                    categories.product_category_name_english,
                    products.product_category_name
                ))::integer AS total_categories
            FROM raw.raw_sellers AS sellers
            LEFT JOIN raw.raw_order_items AS items
                ON items.seller_id = sellers.seller_id
            LEFT JOIN raw.raw_products AS products
                ON products.product_id = items.product_id
            LEFT JOIN raw.raw_categories AS categories
                ON categories.product_category_name
                   = products.product_category_name
            WHERE sellers.seller_id = :seller_id
            GROUP BY sellers.seller_id
            """
        )
        categories_query = text(
            """
            SELECT DISTINCT COALESCE(
                categories.product_category_name_english,
                products.product_category_name
            ) AS category_name
            FROM raw.raw_order_items AS items
            JOIN raw.raw_products AS products
                ON products.product_id = items.product_id
            LEFT JOIN raw.raw_categories AS categories
                ON categories.product_category_name
                   = products.product_category_name
            WHERE items.seller_id = :seller_id
              AND products.product_category_name IS NOT NULL
            ORDER BY category_name
            """
        )
        products_query = text(
            """
            SELECT DISTINCT product_id
            FROM raw.raw_order_items
            WHERE seller_id = :seller_id
            ORDER BY product_id
            LIMIT :product_limit
            """
        )

        with self.engine.connect() as connection:
            summary_row = connection.execute(
                summary_query,
                {"seller_id": seller_id},
            ).mappings().one_or_none()
            if summary_row is None:
                return None

            category_rows = connection.execute(
                categories_query,
                {"seller_id": seller_id},
            ).mappings().all()
            product_rows = connection.execute(
                products_query,
                {
                    "seller_id": seller_id,
                    "product_limit": product_limit,
                },
            ).mappings().all()

        return SellerCatalog(
            seller_id=str(summary_row["seller_id"]),
            total_categories=int(summary_row["total_categories"]),
            total_unique_products=int(summary_row["total_unique_products"]),
            categories=[str(row["category_name"]) for row in category_rows],
            product_ids=[str(row["product_id"]) for row in product_rows],
        )

    def get_seller_top_products(
        self,
        seller_id: str,
        limit: int = 10,
    ) -> list[SellerProductSales]:
        """Получить товары продавца с наибольшей выручкой."""
        query = text(
            """
            SELECT
                items.product_id,
                COALESCE(
                    categories.product_category_name_english,
                    products.product_category_name
                ) AS category_name,
                COUNT(DISTINCT items.order_id)::integer AS total_orders,
                COUNT(*)::integer AS total_items,
                COALESCE(SUM(items.price), 0)::numeric AS total_revenue,
                COALESCE(AVG(items.price), 0)::numeric AS average_price
            FROM raw.raw_order_items AS items
            JOIN raw.raw_orders AS orders
                ON orders.order_id = items.order_id
            JOIN raw.raw_products AS products
                ON products.product_id = items.product_id
            LEFT JOIN raw.raw_categories AS categories
                ON categories.product_category_name
                   = products.product_category_name
            WHERE items.seller_id = :seller_id
              AND orders.order_status = 'delivered'
            GROUP BY
                items.product_id,
                categories.product_category_name_english,
                products.product_category_name
            ORDER BY total_revenue DESC, total_items DESC, items.product_id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {"seller_id": seller_id, "limit": limit},
            ).mappings().all()

        return [
            SellerProductSales(
                product_id=str(row["product_id"]),
                category_name=(
                    str(row["category_name"])
                    if row["category_name"] is not None
                    else None
                ),
                total_orders=int(row["total_orders"]),
                total_items=int(row["total_items"]),
                total_revenue=Decimal(str(row["total_revenue"])),
                average_price=Decimal(str(row["average_price"])),
            )
            for row in rows
        ]

    def find_high_sales_low_rating_sellers(
        self,
        candidate_limit: int = 20,
        result_limit: int = 10,
        max_rating: float | None = None,
    ) -> SellerSalesRatingRanking:
        """Сопоставить топ продавцов по выручке с их рейтингами."""

        query = text(
            """
            WITH seller_sales AS (
                SELECT
                    items.seller_id,
                    COUNT(DISTINCT items.order_id)::integer AS total_orders,
                    SUM(items.price)::numeric AS total_revenue
                FROM raw.raw_order_items AS items
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = items.order_id
                WHERE orders.order_status = 'delivered'
                GROUP BY items.seller_id
            ),
            top_sales AS (
                SELECT seller_id, total_orders, total_revenue
                FROM seller_sales
                ORDER BY total_revenue DESC, seller_id
                LIMIT :candidate_limit
            ),
            seller_orders AS (
                SELECT DISTINCT items.seller_id, items.order_id
                FROM raw.raw_order_items AS items
                JOIN top_sales
                    ON top_sales.seller_id = items.seller_id
            ),
            seller_ratings AS (
                SELECT
                    seller_orders.seller_id,
                    AVG(reviews.review_score)::numeric AS average_rating,
                    COUNT(reviews.review_id)::integer AS total_reviews
                FROM seller_orders
                JOIN raw.raw_reviews AS reviews
                    ON reviews.order_id = seller_orders.order_id
                GROUP BY seller_orders.seller_id
            ),
            market_rating AS (
                SELECT AVG(review_score)::numeric AS average_rating
                FROM raw.raw_reviews
            )
            SELECT
                top_sales.seller_id,
                top_sales.total_orders,
                top_sales.total_revenue,
                seller_ratings.average_rating,
                seller_ratings.total_reviews,
                market_rating.average_rating AS market_average_rating
            FROM top_sales
            LEFT JOIN seller_ratings
                ON seller_ratings.seller_id = top_sales.seller_id
            CROSS JOIN market_rating
            ORDER BY top_sales.total_revenue DESC, top_sales.seller_id
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {"candidate_limit": candidate_limit},
            ).mappings().all()

        market_average = (
            Decimal(str(rows[0]["market_average_rating"]))
            if rows
            else Decimal("0")
        )
        rating_threshold = (
            Decimal(str(max_rating))
            if max_rating is not None
            else market_average
        )

        evaluated_rows = [
            row for row in rows
            if row["average_rating"] is not None
        ]
        selected_rows = [
            row for row in evaluated_rows
            if Decimal(str(row["average_rating"])) < rating_threshold
        ][:result_limit]

        return SellerSalesRatingRanking(
            ranking_metric="total_revenue",
            candidate_pool_size=len(rows),
            evaluated_sellers=len(evaluated_rows),
            rating_threshold=rating_threshold,
            threshold_source=(
                "explicit_max_rating"
                if max_rating is not None
                else "market_average_rating"
            ),
            market_average_rating=market_average,
            sellers=[
                SellerSalesRating(
                    seller_id=str(row["seller_id"]),
                    total_orders=int(row["total_orders"]),
                    total_revenue=Decimal(str(row["total_revenue"])),
                    average_rating=Decimal(str(row["average_rating"])),
                    total_reviews=int(row["total_reviews"]),
                )
                for row in selected_rows
            ],
        )
