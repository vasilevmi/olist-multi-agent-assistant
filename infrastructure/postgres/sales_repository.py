"""PostgreSQL-реализация репозитория продаж."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from domain.sales.entities import (
    CategorySalesSummary,
    Order,
    OrderItem,
    SalesSummary,
    SellerSalesSummary,
)
from domain.sales.repositories import SalesRepository


class PostgresSalesRepository(SalesRepository):
    """Получает данные о продажах из PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        # Engine хранит настройки подключения и выдаёт соединения с PostgreSQL.
        self.engine = engine

    def get_order_by_id(self, order_id: str) -> Order | None:
        """Получить заказ вместе с его позициями."""

        # Получаем одну строку с основной информацией о заказе.
        order_query = text(
            """
            SELECT
                order_id,
                customer_id,
                order_status,
                order_purchase_timestamp::timestamp AS purchase_date
            FROM raw.raw_orders
            WHERE order_id = :order_id
            """
        )

        # Получаем все товарные позиции, которые входят в этот заказ.
        items_query = text(
            """
            SELECT
                order_id,
                order_item_id,
                product_id,
                seller_id,
                price,
                freight_value
            FROM raw.raw_order_items
            WHERE order_id = :order_id
            ORDER BY order_item_id
            """
        )

        with self.engine.connect() as connection:
            # first() возвращает одну строку или None, если заказ не найден.
            order_row = connection.execute(
                order_query,
                {"order_id": order_id},
            ).mappings().first()

            if order_row is None:
                return None

            # all() возвращает список всех позиций найденного заказа.
            item_rows = connection.execute(
                items_query,
                {"order_id": order_id},
            ).mappings().all()

        # Преобразуем строки PostgreSQL в доменные объекты OrderItem.
        items = [
            OrderItem(
                order_id=row["order_id"],
                order_item_id=int(row["order_item_id"]),
                product_id=row["product_id"],
                seller_id=row["seller_id"],
                price=Decimal(str(row["price"])),
                freight_value=Decimal(str(row["freight_value"])),
            )
            for row in item_rows
        ]

        # Собираем заказ и найденные позиции в одну доменную сущность.
        return Order(
            order_id=order_row["order_id"],
            customer_id=order_row["customer_id"],
            status=order_row["order_status"],
            purchase_date=order_row["purchase_date"],
            items=items,
        )

    def get_sales_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SalesSummary:
        """Получить сводку по доставленным заказам за период."""

        # Одним запросом рассчитываем основные показатели продаж.
        summary_query = text(
            """
            WITH filtered_items AS (
                SELECT
                    orders.order_id,
                    items.product_id,
                    items.price
                FROM raw.raw_orders AS orders
                JOIN raw.raw_order_items AS items
                    ON items.order_id = orders.order_id
                WHERE orders.order_status = 'delivered'
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
            ),
            order_totals AS (
                SELECT
                    order_id,
                    SUM(price)::numeric AS order_revenue,
                    COUNT(*)::integer AS item_count
                FROM filtered_items
                GROUP BY order_id
            )
            SELECT
                COUNT(*)::integer AS total_orders,
                COALESCE(SUM(order_revenue), 0)::numeric
                    AS total_revenue,
                COALESCE(AVG(order_revenue), 0)::numeric
                    AS average_order_value,
                COALESCE(SUM(item_count), 0)::integer
                    AS total_items,
                (
                    SELECT COUNT(DISTINCT product_id)::integer
                    FROM filtered_items
                ) AS unique_products
            FROM order_totals
            """
        )

        with self.engine.connect() as connection:
            # Агрегатный SELECT всегда возвращает одну итоговую строку.
            row = connection.execute(
                summary_query,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        # Преобразуем итоговую строку SQL в объект SalesSummary.
        return SalesSummary(
            total_orders=int(row["total_orders"]),
            total_revenue=Decimal(str(row["total_revenue"])),
            average_order_value=Decimal(
                str(row["average_order_value"])
            ),
            total_items=int(row["total_items"]),
            unique_products=int(row["unique_products"]),
        )
    
    def get_seller_sales(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerSalesSummary | None:
        """Получить показатели продаж конкретного продавца."""

        seller_query = text(
            """
            WITH filtered_items AS (
                SELECT
                    items.order_id,
                    items.product_id,
                    items.price
                FROM raw.raw_order_items AS items
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = items.order_id
                WHERE items.seller_id = :seller_id
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
                COUNT(DISTINCT order_id)::integer AS total_orders,
                COALESCE(SUM(price), 0)::numeric AS total_revenue,
                COALESCE(
                    SUM(price) / NULLIF(COUNT(DISTINCT order_id), 0),
                    0
                )::numeric AS average_order_value,
                COUNT(*)::integer AS total_items,
                COUNT(DISTINCT product_id)::integer AS unique_products
            FROM filtered_items
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                seller_query,
                {
                    "seller_id": seller_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        # Если не найдено ни одной позиции, у продавца нет продаж за этот период.
        if row["total_items"] == 0:
            return None

        # Превращаем результат SQL в доменную сущность.
        return SellerSalesSummary(
            seller_id=seller_id,
            total_orders=int(row["total_orders"]),
            total_revenue=Decimal(str(row["total_revenue"])),
            average_order_value=Decimal(
                str(row["average_order_value"])
            ),
            total_items=int(row["total_items"]),
            unique_products=int(row["unique_products"]),
        )    

    def get_sales_by_category(
        self,
        category_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CategorySalesSummary | None:
        """Получить показатели продаж категории."""

        category_query = text(
            """
            WITH filtered_items AS (
                SELECT
                    items.order_id,
                    items.product_id,
                    items.price
                FROM raw.raw_orders AS orders
                JOIN raw.raw_order_items AS items
                    ON items.order_id = orders.order_id
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
                WHERE categories.product_category_name_english
                      = :category_name
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
                COUNT(DISTINCT order_id)::integer AS total_orders,
                COALESCE(SUM(price), 0)::numeric AS total_revenue,
                COALESCE(
                    SUM(price) / NULLIF(COUNT(DISTINCT order_id), 0),
                    0
                )::numeric AS average_order_value,
                COUNT(*)::integer AS total_items,
                COUNT(DISTINCT product_id)::integer
                    AS unique_products
            FROM filtered_items
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                category_query,
                {
                    "category_name": category_name,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        # Ноль позиций означает, что категория или её продажи не найдены.
        if row["total_items"] == 0:
            return None

        return CategorySalesSummary(
            category_name=category_name,
            total_orders=int(row["total_orders"]),
            total_revenue=Decimal(str(row["total_revenue"])),
            average_order_value=Decimal(
                str(row["average_order_value"])
            ),
            total_items=int(row["total_items"]),
            unique_products=int(row["unique_products"]),
        )

    def get_top_sellers(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Получить продавцов с наибольшей выручкой."""

        top_sellers_query = text(
            """
            WITH filtered_items AS (
                SELECT
                    items.seller_id,
                    items.order_id,
                    items.product_id,
                    items.price
                FROM raw.raw_order_items AS items
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = items.order_id
                WHERE orders.order_status = 'delivered'
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
                seller_id,
                COUNT(DISTINCT order_id)::integer AS total_orders,
                SUM(price)::numeric AS total_revenue,
                (
                    SUM(price) / NULLIF(COUNT(DISTINCT order_id), 0)
                )::numeric AS average_order_value,
                COUNT(*)::integer AS total_items,
                COUNT(DISTINCT product_id)::integer
                    AS unique_products
            FROM filtered_items
            GROUP BY seller_id
            ORDER BY total_revenue DESC, seller_id
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                top_sellers_query,
                {
                    "limit": limit,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            SellerSalesSummary(
                seller_id=row["seller_id"],
                total_orders=int(row["total_orders"]),
                total_revenue=Decimal(str(row["total_revenue"])),
                average_order_value=Decimal(
                    str(row["average_order_value"])
                ),
                total_items=int(row["total_items"]),
                unique_products=int(row["unique_products"]),
            )
            for row in rows
        ]

    def get_category_sales_ranking(
        self,
        limit: int = 10,
        ranking_metric: str = "total_revenue",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategorySalesSummary]:
        """Сгруппировать продажи доставленных заказов по категориям."""

        ranking_query = text(
            """
            WITH category_statistics AS (
                SELECT
                    categories.product_category_name_english
                        AS category_name,
                    COUNT(DISTINCT items.order_id)::integer
                        AS total_orders,
                    SUM(items.price::numeric) AS total_revenue,
                    (
                        SUM(items.price::numeric)
                        / NULLIF(COUNT(DISTINCT items.order_id), 0)
                    )::numeric AS average_order_value,
                    COUNT(*)::integer AS total_items,
                    COUNT(DISTINCT items.product_id)::integer
                        AS unique_products
                FROM raw.raw_orders AS orders
                JOIN raw.raw_order_items AS items
                    ON items.order_id = orders.order_id
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
                WHERE orders.order_status = 'delivered'
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
                GROUP BY categories.product_category_name_english
            )
            SELECT *
            FROM category_statistics
            ORDER BY
                CASE
                    WHEN :ranking_metric = 'total_orders'
                    THEN total_orders::numeric
                    WHEN :ranking_metric = 'total_items'
                    THEN total_items::numeric
                    ELSE total_revenue
                END DESC,
                total_revenue DESC,
                category_name
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                ranking_query,
                {
                    "limit": limit,
                    "ranking_metric": ranking_metric,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            CategorySalesSummary(
                category_name=str(row["category_name"]),
                total_orders=int(row["total_orders"]),
                total_revenue=Decimal(str(row["total_revenue"])),
                average_order_value=Decimal(
                    str(row["average_order_value"])
                ),
                total_items=int(row["total_items"]),
                unique_products=int(row["unique_products"]),
            )
            for row in rows
        ]

    def compare_sellers(
        self,
        seller_ids: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerSalesSummary]:
        """Получить показатели выбранных продавцов."""

        compare_query = text(
            """
            WITH filtered_items AS (
                SELECT
                    items.seller_id,
                    items.order_id,
                    items.product_id,
                    items.price
                FROM raw.raw_order_items AS items
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = items.order_id
                WHERE items.seller_id IN :seller_ids
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
                seller_id,
                COUNT(DISTINCT order_id)::integer AS total_orders,
                SUM(price)::numeric AS total_revenue,
                (
                    SUM(price) / NULLIF(COUNT(DISTINCT order_id), 0)
                )::numeric AS average_order_value,
                COUNT(*)::integer AS total_items,
                COUNT(DISTINCT product_id)::integer
                    AS unique_products
            FROM filtered_items
            GROUP BY seller_id
            ORDER BY total_revenue DESC, seller_id
            """
        ).bindparams(bindparam("seller_ids", expanding=True))

        with self.engine.connect() as connection:
            rows = connection.execute(
                compare_query,
                {
                    "seller_ids": seller_ids,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            SellerSalesSummary(
                seller_id=row["seller_id"],
                total_orders=int(row["total_orders"]),
                total_revenue=Decimal(str(row["total_revenue"])),
                average_order_value=Decimal(
                    str(row["average_order_value"])
                ),
                total_items=int(row["total_items"]),
                unique_products=int(row["unique_products"]),
            )
            for row in rows
        ]
