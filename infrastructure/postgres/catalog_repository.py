"""PostgreSQL-реализация репозитория каталога."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from domain.catalog.entities import Category, Product, ProductStatistics
from domain.catalog.repositories import CatalogRepository


class PostgresCatalogRepository(CatalogRepository):
    """Получает товары и категории из PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _optional_decimal(value: Any) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    @classmethod
    def _product_from_row(cls, row: Any) -> Product:
        """Преобразовать строку SQL в сущность Product."""
        return Product(
            product_id=str(row["product_id"]),
            category_name_original=row["category_name_original"],
            category_name_english=row["category_name_english"],
            name_length=cls._optional_int(row["name_length"]),
            description_length=cls._optional_int(row["description_length"]),
            photos_quantity=cls._optional_int(row["photos_quantity"]),
            weight_g=cls._optional_decimal(row["weight_g"]),
            length_cm=cls._optional_decimal(row["length_cm"]),
            height_cm=cls._optional_decimal(row["height_cm"]),
            width_cm=cls._optional_decimal(row["width_cm"]),
        )

    def get_product(self, product_id: str) -> Product | None:
        """Получить карточку товара по идентификатору."""
        query = text(
            """
            SELECT
                products.product_id,
                products.product_category_name
                    AS category_name_original,
                categories.product_category_name_english
                    AS category_name_english,
                products.product_name_lenght AS name_length,
                products.product_description_lenght
                    AS description_length,
                products.product_photos_qty AS photos_quantity,
                products.product_weight_g AS weight_g,
                products.product_length_cm AS length_cm,
                products.product_height_cm AS height_cm,
                products.product_width_cm AS width_cm
            FROM raw.raw_products AS products
            LEFT JOIN raw.raw_categories AS categories
                ON categories.product_category_name
                   = products.product_category_name
            WHERE products.product_id = :product_id
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {"product_id": product_id},
            ).mappings().one_or_none()
        return None if row is None else self._product_from_row(row)

    def get_category(self, category_name: str) -> Category | None:
        """Получить категорию по английскому или оригинальному названию."""
        query = text(
            """
            SELECT
                categories.product_category_name
                    AS category_name_original,
                categories.product_category_name_english
                    AS category_name_english,
                COUNT(products.product_id)::integer AS total_products
            FROM raw.raw_categories AS categories
            LEFT JOIN raw.raw_products AS products
                ON products.product_category_name
                   = categories.product_category_name
            WHERE LOWER(categories.product_category_name_english)
                      = LOWER(:category_name)
               OR LOWER(categories.product_category_name)
                      = LOWER(:category_name)
            GROUP BY
                categories.product_category_name,
                categories.product_category_name_english
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {"category_name": category_name},
            ).mappings().one_or_none()
        if row is None:
            return None
        return Category(
            category_name_original=str(row["category_name_original"]),
            category_name_english=str(row["category_name_english"]),
            total_products=int(row["total_products"]),
        )

    def get_category_products(
        self,
        category_name: str,
        limit: int = 20,
    ) -> list[Product]:
        """Получить товары категории по английскому или исходному названию."""
        query = text(
            """
            SELECT
                products.product_id,
                products.product_category_name
                    AS category_name_original,
                categories.product_category_name_english
                    AS category_name_english,
                products.product_name_lenght AS name_length,
                products.product_description_lenght
                    AS description_length,
                products.product_photos_qty AS photos_quantity,
                products.product_weight_g AS weight_g,
                products.product_length_cm AS length_cm,
                products.product_height_cm AS height_cm,
                products.product_width_cm AS width_cm
            FROM raw.raw_products AS products
            JOIN raw.raw_categories AS categories
                ON categories.product_category_name
                   = products.product_category_name
            WHERE LOWER(categories.product_category_name_english)
                      = LOWER(:category_name)
               OR LOWER(categories.product_category_name)
                      = LOWER(:category_name)
            ORDER BY products.product_id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {"category_name": category_name, "limit": limit},
            ).mappings().all()
        return [self._product_from_row(row) for row in rows]

    def get_product_statistics(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductStatistics | None:
        """Получить показатели завершённых продаж товара за период."""
        query = text(
            """
            WITH filtered_items AS (
                SELECT
                    items.product_id,
                    items.order_id,
                    items.seller_id,
                    items.price
                FROM raw.raw_order_items AS items
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = items.order_id
                WHERE items.product_id = :product_id
                  AND orders.order_status = 'delivered'
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
                products.product_id,
                COUNT(DISTINCT filtered_items.order_id)::integer
                    AS total_orders,
                COUNT(filtered_items.product_id)::integer AS total_items,
                COALESCE(SUM(filtered_items.price), 0)::numeric
                    AS total_revenue,
                COALESCE(AVG(filtered_items.price), 0)::numeric
                    AS average_price,
                COUNT(DISTINCT filtered_items.seller_id)::integer
                    AS unique_sellers
            FROM raw.raw_products AS products
            LEFT JOIN filtered_items
                ON filtered_items.product_id = products.product_id
            WHERE products.product_id = :product_id
            GROUP BY products.product_id
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query,
                {
                    "product_id": product_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one_or_none()
        if row is None:
            return None
        return ProductStatistics(
            product_id=str(row["product_id"]),
            total_orders=int(row["total_orders"]),
            total_items=int(row["total_items"]),
            total_revenue=Decimal(str(row["total_revenue"])),
            average_price=Decimal(str(row["average_price"])),
            unique_sellers=int(row["unique_sellers"]),
        )
