"""Ручная проверка репозитория продаж."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from application.sales.use_cases import (
    GetOrderById,
    GetSalesSummary,
    GetSellerSales,
)
from infrastructure.postgres.sales_repository import PostgresSalesRepository


def main() -> None:
    # Находим корень проекта и загружаем настройки базы из .env.
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    database_url = (
        f"postgresql://{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )

    # Создаём Engine и передаём его PostgreSQL-репозиторию.
    engine = create_engine(database_url)
    repository = PostgresSalesRepository(engine)
    get_order = GetOrderById(repository)
    get_summary = GetSalesSummary(repository)
    get_seller_sales = GetSellerSales(repository)
    # Этот order_id существует в исходном датасете Olist.
    order_id = "e481f51cbdc54678b7cc49136f2d6af7"

    try:
        order = get_order.execute(order_id)

        if order is None:
            print("Заказ не найден")
            return

        print("Заказ найден")
        print("ID:", order.order_id)
        print("Покупатель:", order.customer_id)
        print("Статус:", order.status)
        print("Дата покупки:", order.purchase_date)
        print("Количество позиций:", order.item_count)
        print("Продавцы:", order.unique_sellers)
        print("Общая сумма:", order.total_amount)

        print("\nПозиции:")

        for item in order.items:
            print(
                f"product={item.product_id}, "
                f"seller={item.seller_id}, "
                f"price={item.price}, "
                f"freight={item.freight_value}, "
                f"total={item.total_amount}"
            )

        # Проверяем второй метод репозитория на всём доступном периоде.
        summary = get_summary.execute()

        print("\nСводка продаж:")
        print("Заказов:", summary.total_orders)
        print("Выручка:", summary.formatted_revenue)
        print("Средний чек:", summary.formatted_average_order)
        print("Позиций:", summary.total_items)
        print("Уникальных товаров:", summary.unique_products)

        # Проверяем продажи продавца из выбранного выше заказа.
        seller_id = "3504c0cb71d7fa48d967e0e4c94d59d9"
        seller_summary = get_seller_sales.execute(seller_id)

        print("\nПродажи продавца:")

        if seller_summary is None:
            print("Продажи продавца не найдены")
        else:
            print("ID продавца:", seller_summary.seller_id)
            print("Заказов:", seller_summary.total_orders)
            print("Выручка:", seller_summary.formatted_revenue)
            print(
                "Средняя сумма на заказ:",
                seller_summary.formatted_average_order,
            )
            print("Проданных позиций:", seller_summary.total_items)
            print(
                "Уникальных товаров:",
                seller_summary.unique_products,
            )
    finally:
        # Закрываем пул соединений SQLAlchemy.
        engine.dispose()


if __name__ == "__main__":
    main()
