import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

load_dotenv(PROJECT_ROOT / ".env")

# Подключение к БД
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

FILES = {
    'olist_customers_dataset.csv': 'raw_customers',
    'olist_orders_dataset.csv': 'raw_orders',
    'olist_order_items_dataset.csv': 'raw_order_items',
    'olist_products_dataset.csv': 'raw_products',
    'olist_sellers_dataset.csv': 'raw_sellers',
    'olist_order_payments_dataset.csv': 'raw_payments',
    'olist_order_reviews_dataset.csv': 'raw_reviews',
    'olist_geolocation_dataset.csv': 'raw_geolocation',
    'product_category_name_translation.csv': 'raw_categories'
}

def load_raw_data():
    """Загружает все CSV файлы в raw-таблицы"""
    loaded_tables = 0

    # Одна транзакция и одно соединение: созданная схема сразу видна pandas.
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE SCHEMA IF NOT EXISTS raw;
        """))
        
        for filename, table_name in FILES.items():
            filepath = DATA_DIR / filename
            if not filepath.exists():
                logger.warning(f"Файл {filepath} не найден, пропускаем")
                continue
                
            logger.info(f"Загрузка {filename} в raw.{table_name}")
            
            df = pd.read_csv(filepath)
            
            df.to_sql(
                table_name,
                conn,
                schema='raw',
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )
            loaded_tables += 1
            
            logger.info(f"Загружено {len(df)} записей в raw.{table_name}")

    if loaded_tables != len(FILES):
        raise RuntimeError(
            f"Загружено таблиц: {loaded_tables} из {len(FILES)}. "
            f"Проверьте CSV в {DATA_DIR}"
        )

if __name__ == "__main__":
    load_raw_data()
    logger.info(" Все данные загружены!")
