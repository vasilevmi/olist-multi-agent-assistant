"""Интерфейс доступа к данным продавцов."""

from abc import ABC, abstractmethod

from domain.seller.entities import (
    Seller,
    SellerCatalog,
    SellerProductSales,
    SellerSalesRatingRanking,
)


class SellerRepository(ABC):
    """Договор получения основной информации о продавцах."""

    @abstractmethod
    def get_seller(self, seller_id: str) -> Seller | None:
        """Вернуть продавца либо None, если он не найден."""

    @abstractmethod
    def get_sellers_by_location(
        self,
        state: str | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[Seller]:
        """Вернуть продавцов выбранного штата или города."""

    @abstractmethod
    def get_seller_catalog(
        self,
        seller_id: str,
        product_limit: int = 20,
    ) -> SellerCatalog | None:
        """Вернуть категории и уникальные товары продавца."""

    @abstractmethod
    def get_seller_top_products(
        self,
        seller_id: str,
        limit: int = 10,
    ) -> list[SellerProductSales]:
        """Вернуть самые продаваемые товары продавца по выручке."""

    @abstractmethod
    def find_high_sales_low_rating_sellers(
        self,
        candidate_limit: int = 20,
        result_limit: int = 10,
        max_rating: float | None = None,
    ) -> SellerSalesRatingRanking:
        """Найти продавцов из топа выручки с рейтингом ниже порога."""
