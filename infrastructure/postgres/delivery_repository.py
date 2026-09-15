"""PostgreSQL-реализация репозитория доставки."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine

from domain.delivery.entities import (
    CategoryDeliveryPerformance,
    Delivery,
    DeliveryStatistics,
    RegionDeliveryPerformance,
    SellerDeliveryPerformance,
)
from domain.delivery.repositories import DeliveryRepository


class PostgresDeliveryRepository(DeliveryRepository):
    """Получает данные о доставке из PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_delivery_by_order_id(
        self,
        order_id: str,
    ) -> Delivery | None:
        """Получить информацию о доставке одного заказа."""

        delivery_query = text(
            """
            SELECT
                order_id,
                order_purchase_timestamp::timestamp
                    AS purchase_date,
                order_delivered_customer_date::timestamp
                    AS delivered_date,
                order_estimated_delivery_date::timestamp
                    AS estimated_delivery_date
            FROM raw.raw_orders
            WHERE order_id = :order_id
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                delivery_query,
                {
                    "order_id": order_id,
                },
            ).mappings().first()

        if row is None:
            return None

        return Delivery(
            order_id=row["order_id"],
            purchase_date=row["purchase_date"],
            delivered_date=row["delivered_date"],
            estimated_delivery_date=(
                row["estimated_delivery_date"]
            ),
        )

    def get_delivery_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryStatistics:
        """Получить общую статистику доставки за период."""

        statistics_query = text(
            """
            WITH filtered_deliveries AS (
                SELECT
                    order_purchase_timestamp::timestamp
                        AS purchase_date,
                    order_delivered_customer_date::timestamp
                        AS delivered_date,
                    order_estimated_delivery_date::timestamp
                        AS estimated_delivery_date
                FROM raw.raw_orders
                WHERE order_status = 'delivered'
                  AND order_delivered_customer_date IS NOT NULL
                  AND order_estimated_delivery_date IS NOT NULL
                  AND (
                      CAST(:start_date AS timestamp) IS NULL
                      OR order_purchase_timestamp::timestamp
                         >= CAST(:start_date AS timestamp)
                  )
                  AND (
                      CAST(:end_date AS timestamp) IS NULL
                      OR order_purchase_timestamp::timestamp
                         < CAST(:end_date AS timestamp)
                  )
            )
            SELECT
                COUNT(*)::integer AS total_delivered_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date > estimated_delivery_date
                )::integer AS delayed_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date <= estimated_delivery_date
                )::integer AS on_time_orders,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    )::numeric
                    / NULLIF(COUNT(*), 0),
                    0
                )::numeric AS delayed_share,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM delivered_date - purchase_date
                        ) / 86400
                    ),
                    0
                )::numeric AS average_delivery_days,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM
                            delivered_date - estimated_delivery_date
                        ) / 86400
                    ) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    ),
                    0
                )::numeric AS average_delay_days
            FROM filtered_deliveries
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                statistics_query,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        return DeliveryStatistics(
            total_delivered_orders=int(
                row["total_delivered_orders"]
            ),
            delayed_orders=int(row["delayed_orders"]),
            on_time_orders=int(row["on_time_orders"]),
            delayed_share=Decimal(
                str(row["delayed_share"])
            ),
            average_delivery_days=Decimal(
                str(row["average_delivery_days"])
            ),
            average_delay_days=Decimal(
                str(row["average_delay_days"])
            ),
        )

    def get_delayed_orders(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Delivery]:
        """Получить самые сильно задержанные заказы."""

        delayed_orders_query = text(
            """
            SELECT
                order_id,
                order_purchase_timestamp::timestamp
                    AS purchase_date,
                order_delivered_customer_date::timestamp
                    AS delivered_date,
                order_estimated_delivery_date::timestamp
                    AS estimated_delivery_date
            FROM raw.raw_orders
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
              AND order_estimated_delivery_date IS NOT NULL
              AND order_delivered_customer_date::timestamp
                  > order_estimated_delivery_date::timestamp
              AND (
                  CAST(:start_date AS timestamp) IS NULL
                  OR order_purchase_timestamp::timestamp
                     >= CAST(:start_date AS timestamp)
              )
              AND (
                  CAST(:end_date AS timestamp) IS NULL
                  OR order_purchase_timestamp::timestamp
                     < CAST(:end_date AS timestamp)
              )
            ORDER BY
                order_delivered_customer_date::timestamp
                - order_estimated_delivery_date::timestamp DESC,
                order_id
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                delayed_orders_query,
                {
                    "limit": limit,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            Delivery(
                order_id=row["order_id"],
                purchase_date=row["purchase_date"],
                delivered_date=row["delivered_date"],
                estimated_delivery_date=(
                    row["estimated_delivery_date"]
                ),
            )
            for row in rows
        ]

    def get_seller_delivery_performance(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerDeliveryPerformance | None:
        """Получить показатели доставки конкретного продавца."""

        performance_query = text(
            """
            WITH seller_orders AS (
                SELECT DISTINCT order_id
                FROM raw.raw_order_items
                WHERE seller_id = :seller_id
            ),
            filtered_deliveries AS (
                SELECT
                    orders.order_purchase_timestamp::timestamp
                        AS purchase_date,
                    orders.order_delivered_customer_date::timestamp
                        AS delivered_date,
                    orders.order_estimated_delivery_date::timestamp
                        AS estimated_delivery_date
                FROM seller_orders
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = seller_orders.order_id
                WHERE orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
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
                COUNT(*)::integer AS total_delivered_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date > estimated_delivery_date
                )::integer AS delayed_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date <= estimated_delivery_date
                )::integer AS on_time_orders,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    )::numeric
                    / NULLIF(COUNT(*), 0),
                    0
                )::numeric AS delayed_share,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM delivered_date - purchase_date
                        ) / 86400
                    ),
                    0
                )::numeric AS average_delivery_days,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM
                            delivered_date - estimated_delivery_date
                        ) / 86400
                    ) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    ),
                    0
                )::numeric AS average_delay_days
            FROM filtered_deliveries
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                performance_query,
                {
                    "seller_id": seller_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        if row["total_delivered_orders"] == 0:
            return None

        return SellerDeliveryPerformance(
            seller_id=seller_id,
            total_delivered_orders=int(
                row["total_delivered_orders"]
            ),
            delayed_orders=int(row["delayed_orders"]),
            on_time_orders=int(row["on_time_orders"]),
            delayed_share=Decimal(str(row["delayed_share"])),
            average_delivery_days=Decimal(
                str(row["average_delivery_days"])
            ),
            average_delay_days=Decimal(
                str(row["average_delay_days"])
            ),
        )

    def get_delivery_by_region(
        self,
        region: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RegionDeliveryPerformance | None:
        """Получить показатели доставки в штате покупателя."""

        region_query = text(
            """
            WITH filtered_deliveries AS (
                SELECT
                    orders.order_purchase_timestamp::timestamp
                        AS purchase_date,
                    orders.order_delivered_customer_date::timestamp
                        AS delivered_date,
                    orders.order_estimated_delivery_date::timestamp
                        AS estimated_delivery_date
                FROM raw.raw_orders AS orders
                JOIN raw.raw_customers AS customers
                    ON customers.customer_id = orders.customer_id
                WHERE customers.customer_state = :region
                  AND orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
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
                COUNT(*)::integer AS total_delivered_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date > estimated_delivery_date
                )::integer AS delayed_orders,
                COUNT(*) FILTER (
                    WHERE delivered_date <= estimated_delivery_date
                )::integer AS on_time_orders,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    )::numeric
                    / NULLIF(COUNT(*), 0),
                    0
                )::numeric AS delayed_share,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM delivered_date - purchase_date
                        ) / 86400
                    ),
                    0
                )::numeric AS average_delivery_days,
                COALESCE(
                    AVG(
                        EXTRACT(
                            EPOCH FROM
                            delivered_date - estimated_delivery_date
                        ) / 86400
                    ) FILTER (
                        WHERE delivered_date > estimated_delivery_date
                    ),
                    0
                )::numeric AS average_delay_days
            FROM filtered_deliveries
            """
        )

        with self.engine.connect() as connection:
            row = connection.execute(
                region_query,
                {
                    "region": region,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().one()

        if row["total_delivered_orders"] == 0:
            return None

        return RegionDeliveryPerformance(
            region=region,
            total_delivered_orders=int(
                row["total_delivered_orders"]
            ),
            delayed_orders=int(row["delayed_orders"]),
            on_time_orders=int(row["on_time_orders"]),
            delayed_share=Decimal(str(row["delayed_share"])),
            average_delivery_days=Decimal(
                str(row["average_delivery_days"])
            ),
            average_delay_days=Decimal(
                str(row["average_delay_days"])
            ),
        )

    def find_sellers_by_delay_rate(
        self,
        delay_threshold: float = 0.20,
        min_orders: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerDeliveryPerformance]:
        """Найти продавцов, чья доля задержек превышает порог."""

        query = text(
            """
            WITH seller_orders AS (
                SELECT DISTINCT seller_id, order_id
                FROM raw.raw_order_items
            ),
            seller_statistics AS (
                SELECT
                    seller_orders.seller_id,
                    COUNT(*)::integer AS total_delivered_orders,
                    COUNT(*) FILTER (
                        WHERE orders.order_delivered_customer_date::timestamp
                              > orders.order_estimated_delivery_date::timestamp
                    )::integer AS delayed_orders,
                    COUNT(*) FILTER (
                        WHERE orders.order_delivered_customer_date::timestamp
                              <= orders.order_estimated_delivery_date::timestamp
                    )::integer AS on_time_orders,
                    (
                        COUNT(*) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        )::numeric / NULLIF(COUNT(*), 0)
                    )::numeric AS delayed_share,
                    AVG(EXTRACT(EPOCH FROM (
                        orders.order_delivered_customer_date::timestamp
                        - orders.order_purchase_timestamp::timestamp
                    )) / 86400)::numeric AS average_delivery_days,
                    COALESCE(
                        AVG(EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_estimated_delivery_date::timestamp
                        )) / 86400) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        ),
                        0
                    )::numeric AS average_delay_days
                FROM seller_orders
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = seller_orders.order_id
                WHERE orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
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
                GROUP BY seller_orders.seller_id
            )
            SELECT *
            FROM seller_statistics
            WHERE total_delivered_orders >= :min_orders
              AND delayed_share > :delay_threshold
            ORDER BY delayed_share DESC, delayed_orders DESC, seller_id
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "delay_threshold": delay_threshold,
                    "min_orders": min_orders,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            SellerDeliveryPerformance(
                seller_id=str(row["seller_id"]),
                total_delivered_orders=int(row["total_delivered_orders"]),
                delayed_orders=int(row["delayed_orders"]),
                on_time_orders=int(row["on_time_orders"]),
                delayed_share=Decimal(str(row["delayed_share"])),
                average_delivery_days=Decimal(
                    str(row["average_delivery_days"])
                ),
                average_delay_days=Decimal(str(row["average_delay_days"])),
            )
            for row in rows
        ]

    def get_category_delivery_ranking(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryDeliveryPerformance]:
        """Сгруппировать доставленные заказы по товарным категориям."""

        ranking_query = text(
            """
            WITH category_orders AS (
                SELECT DISTINCT
                    COALESCE(
                        categories.product_category_name_english,
                        products.product_category_name
                    ) AS category_name,
                    items.order_id
                FROM raw.raw_order_items AS items
                JOIN raw.raw_products AS products
                    ON products.product_id = items.product_id
                LEFT JOIN raw.raw_categories AS categories
                    ON categories.product_category_name
                       = products.product_category_name
                WHERE products.product_category_name IS NOT NULL
            ),
            category_statistics AS (
                SELECT
                    category_orders.category_name,
                    COUNT(*)::integer AS total_delivered_orders,
                    COUNT(*) FILTER (
                        WHERE orders.order_delivered_customer_date::timestamp
                              > orders.order_estimated_delivery_date::timestamp
                    )::integer AS delayed_orders,
                    COALESCE(
                        COUNT(*) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        )::numeric / NULLIF(COUNT(*), 0),
                        0
                    )::numeric AS delayed_share,
                    COALESCE(
                        AVG(EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_purchase_timestamp::timestamp
                        )) / 86400),
                        0
                    )::numeric AS average_delivery_days,
                    COALESCE(
                        AVG(EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_estimated_delivery_date::timestamp
                        )) / 86400) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        ),
                        0
                    )::numeric AS average_delay_days
                FROM category_orders
                JOIN raw.raw_orders AS orders
                    ON orders.order_id = category_orders.order_id
                WHERE orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
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
                GROUP BY category_orders.category_name
            )
            SELECT *
            FROM category_statistics
            WHERE total_delivered_orders >= :min_orders
            ORDER BY
                CASE
                    WHEN :ranking_metric = 'delayed_orders'
                    THEN delayed_orders::numeric
                    ELSE delayed_share
                END DESC,
                delayed_orders DESC,
                category_name
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                ranking_query,
                {
                    "limit": limit,
                    "min_orders": min_orders,
                    "ranking_metric": ranking_metric,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            CategoryDeliveryPerformance(
                category_name=str(row["category_name"]),
                total_delivered_orders=int(row["total_delivered_orders"]),
                delayed_orders=int(row["delayed_orders"]),
                delayed_share=Decimal(str(row["delayed_share"])),
                average_delivery_days=Decimal(
                    str(row["average_delivery_days"])
                ),
                average_delay_days=Decimal(str(row["average_delay_days"])),
            )
            for row in rows
        ]

    def get_region_delivery_ranking(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RegionDeliveryPerformance]:
        """Сгруппировать показатели доставки по штатам покупателей."""

        ranking_query = text(
            """
            WITH region_statistics AS (
                SELECT
                    customers.customer_state AS region,
                    COUNT(*)::integer AS total_delivered_orders,
                    COUNT(*) FILTER (
                        WHERE orders.order_delivered_customer_date::timestamp
                              > orders.order_estimated_delivery_date::timestamp
                    )::integer AS delayed_orders,
                    COUNT(*) FILTER (
                        WHERE orders.order_delivered_customer_date::timestamp
                              <= orders.order_estimated_delivery_date::timestamp
                    )::integer AS on_time_orders,
                    COALESCE(
                        COUNT(*) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        )::numeric / NULLIF(COUNT(*), 0),
                        0
                    )::numeric AS delayed_share,
                    COALESCE(
                        AVG(EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_purchase_timestamp::timestamp
                        )) / 86400),
                        0
                    )::numeric AS average_delivery_days,
                    COALESCE(
                        AVG(EXTRACT(EPOCH FROM (
                            orders.order_delivered_customer_date::timestamp
                            - orders.order_estimated_delivery_date::timestamp
                        )) / 86400) FILTER (
                            WHERE orders.order_delivered_customer_date::timestamp
                                  > orders.order_estimated_delivery_date::timestamp
                        ),
                        0
                    )::numeric AS average_delay_days
                FROM raw.raw_orders AS orders
                JOIN raw.raw_customers AS customers
                    ON customers.customer_id = orders.customer_id
                WHERE orders.order_status = 'delivered'
                  AND orders.order_delivered_customer_date IS NOT NULL
                  AND orders.order_estimated_delivery_date IS NOT NULL
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
                GROUP BY customers.customer_state
            )
            SELECT *
            FROM region_statistics
            WHERE total_delivered_orders >= :min_orders
            ORDER BY
                CASE
                    WHEN :ranking_metric = 'delayed_orders'
                    THEN delayed_orders::numeric
                    WHEN :ranking_metric = 'average_delivery_days'
                    THEN average_delivery_days
                    ELSE delayed_share
                END DESC,
                delayed_orders DESC,
                region
            LIMIT :limit
            """
        )

        with self.engine.connect() as connection:
            rows = connection.execute(
                ranking_query,
                {
                    "limit": limit,
                    "min_orders": min_orders,
                    "ranking_metric": ranking_metric,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()

        return [
            RegionDeliveryPerformance(
                region=str(row["region"]),
                total_delivered_orders=int(row["total_delivered_orders"]),
                delayed_orders=int(row["delayed_orders"]),
                on_time_orders=int(row["on_time_orders"]),
                delayed_share=Decimal(str(row["delayed_share"])),
                average_delivery_days=Decimal(
                    str(row["average_delivery_days"])
                ),
                average_delay_days=Decimal(str(row["average_delay_days"])),
            )
            for row in rows
        ]
