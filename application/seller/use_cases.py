"""Сценарии получения основной информации о продавцах."""

from domain.seller.entities import (
    Seller,
    SellerCatalog,
    SellerProductSales,
    SellerSalesRatingRanking,
)
from domain.seller.repositories import SellerRepository


class GetSeller:
    """Получить карточку конкретного продавца."""

    def __init__(self, repository: SellerRepository) -> None:
        self.repository = repository

    def execute(self, seller_id: str) -> Seller | None:
        seller_id = seller_id.strip()
        if not seller_id:
            raise ValueError("seller_id не должен быть пустым")
        return self.repository.get_seller(seller_id)


class GetSellersByLocation:
    """Найти продавцов по штату и/или городу."""

    def __init__(self, repository: SellerRepository) -> None:
        self.repository = repository

    def execute(
        self,
        state: str | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[Seller]:
        state = state.strip().upper() if state is not None else None
        city = city.strip() if city is not None else None

        if state == "":
            state = None
        if city == "":
            city = None
        if state is not None and len(state) != 2:
            raise ValueError("state должен состоять из двух букв, например SP")
        if state is None and city is None:
            raise ValueError("Нужно передать state или city")
        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")

        return self.repository.get_sellers_by_location(state, city, limit)


class GetSellerCatalog:
    """Получить категории и уникальные товары продавца."""

    def __init__(self, repository: SellerRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        product_limit: int = 20,
    ) -> SellerCatalog | None:
        seller_id = seller_id.strip()
        if not seller_id:
            raise ValueError("seller_id не должен быть пустым")
        if product_limit < 1 or product_limit > 100:
            raise ValueError("product_limit должен быть от 1 до 100")
        return self.repository.get_seller_catalog(seller_id, product_limit)


class GetSellerTopProducts:
    """Получить товары продавца с наибольшей выручкой."""

    def __init__(self, repository: SellerRepository) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        limit: int = 10,
    ) -> list[SellerProductSales] | None:
        seller_id = seller_id.strip()
        if not seller_id:
            raise ValueError("seller_id не должен быть пустым")
        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")
        if self.repository.get_seller(seller_id) is None:
            return None
        return self.repository.get_seller_top_products(seller_id, limit)


class FindHighSalesLowRatingSellers:
    """Найти продавцов из топа выручки с низким рейтингом."""

    def __init__(self, repository: SellerRepository) -> None:
        self.repository = repository

    def execute(
        self,
        candidate_limit: int = 20,
        result_limit: int = 10,
        max_rating: float | None = None,
    ) -> SellerSalesRatingRanking:
        if candidate_limit < 1 or candidate_limit > 100:
            raise ValueError("candidate_limit должен быть от 1 до 100")
        if result_limit < 1 or result_limit > 100:
            raise ValueError("result_limit должен быть от 1 до 100")
        if result_limit > candidate_limit:
            raise ValueError(
                "result_limit не должен превышать candidate_limit"
            )
        if max_rating is not None and not 1 <= max_rating <= 5:
            raise ValueError("max_rating должен быть от 1 до 5")

        return self.repository.find_high_sales_low_rating_sellers(
            candidate_limit=candidate_limit,
            result_limit=result_limit,
            max_rating=max_rating,
        )
