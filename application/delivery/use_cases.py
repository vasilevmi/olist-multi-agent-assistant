"""Сценарии использования контекста доставки."""

from datetime import datetime

from domain.delivery.entities import (
    CategoryDeliveryPerformance,
    Delivery,
    DeliveryStatistics,
    RegionDeliveryPerformance,
    SellerDeliveryPerformance,
)
from domain.delivery.repositories import DeliveryRepository


class GetDeliveryByOrderId:
    """Сценарий получения доставки одного заказа."""

    def __init__(
        self,
        repository: DeliveryRepository,
    ) -> None:
        self.repository = repository

    def execute(
        self,
        order_id: str,
    ) -> Delivery | None:
        """Проверить ID и получить информацию о доставке."""

        normalized_order_id = order_id.strip()

        if not normalized_order_id:
            raise ValueError(
                "order_id не должен быть пустым"
            )

        return self.repository.get_delivery_by_order_id(
            normalized_order_id
        )


class GetDeliveryStatistics:
    """Сценарий получения общей статистики доставки."""

    def __init__(
        self,
        repository: DeliveryRepository,
    ) -> None:
        self.repository = repository

    def execute(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeliveryStatistics:
        """Проверить период и получить статистику доставки."""

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_delivery_statistics(
            start_date=start_date,
            end_date=end_date,
        )


class GetDelayedOrders:
    """Сценарий получения самых сильно задержанных заказов."""

    def __init__(
        self,
        repository: DeliveryRepository,
    ) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Delivery]:
        """Проверить параметры и получить задержанные заказы."""

        if limit < 1 or limit > 100:
            raise ValueError("limit должен быть от 1 до 100")

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_delayed_orders(
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )


class GetSellerDeliveryPerformance:
    """Сценарий анализа доставки конкретного продавца."""

    def __init__(
        self,
        repository: DeliveryRepository,
    ) -> None:
        self.repository = repository

    def execute(
        self,
        seller_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SellerDeliveryPerformance | None:
        """Проверить параметры и получить показатели продавца."""

        normalized_seller_id = seller_id.strip()

        if not normalized_seller_id:
            raise ValueError("seller_id не должен быть пустым")

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_seller_delivery_performance(
            seller_id=normalized_seller_id,
            start_date=start_date,
            end_date=end_date,
        )


class FindSellersByDelayRate:
    """Найти продавцов с высокой долей задержанных заказов."""

    def __init__(self, repository: DeliveryRepository) -> None:
        self.repository = repository

    def execute(
        self,
        delay_threshold: float = 0.20,
        min_orders: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SellerDeliveryPerformance]:
        if delay_threshold < 0 or delay_threshold >= 1:
            raise ValueError(
                "delay_threshold должен быть долей от 0 включительно до 1"
            )
        if min_orders < 1:
            raise ValueError("min_orders должен быть больше нуля")
        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError("end_date должна быть позже start_date")

        return self.repository.find_sellers_by_delay_rate(
            delay_threshold=delay_threshold,
            min_orders=min_orders,
            start_date=start_date,
            end_date=end_date,
        )


class GetDeliveryByRegion:
    """Сценарий получения показателей доставки по региону."""

    def __init__(
        self,
        repository: DeliveryRepository,
    ) -> None:
        self.repository = repository

    def execute(
        self,
        region: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RegionDeliveryPerformance | None:
        """Проверить параметры и получить показатели региона."""

        normalized_region = region.strip().upper()

        if len(normalized_region) != 2:
            raise ValueError(
                "region должен быть двухбуквенным кодом штата"
            )

        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError(
                "end_date должна быть позже start_date"
            )

        return self.repository.get_delivery_by_region(
            region=normalized_region,
            start_date=start_date,
            end_date=end_date,
        )


class GetCategoryDeliveryRanking:
    """Сценарий построения рейтинга категорий по задержкам доставки."""

    def __init__(self, repository: DeliveryRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategoryDeliveryPerformance]:
        """Проверить параметры и получить рейтинг категорий."""

        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        if min_orders < 1:
            raise ValueError("min_orders должен быть больше нуля")
        if ranking_metric not in {"delayed_share", "delayed_orders"}:
            raise ValueError(
                "ranking_metric должен быть delayed_share или delayed_orders"
            )
        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError("end_date должна быть позже start_date")

        return self.repository.get_category_delivery_ranking(
            limit=limit,
            min_orders=min_orders,
            ranking_metric=ranking_metric,
            start_date=start_date,
            end_date=end_date,
        )


class GetRegionDeliveryRanking:
    """Сценарий построения рейтинга регионов по задержкам доставки."""

    def __init__(self, repository: DeliveryRepository) -> None:
        self.repository = repository

    def execute(
        self,
        limit: int = 10,
        min_orders: int = 100,
        ranking_metric: str = "delayed_share",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RegionDeliveryPerformance]:
        """Проверить параметры и получить рейтинг регионов."""

        if limit < 1 or limit > 50:
            raise ValueError("limit должен быть от 1 до 50")
        if min_orders < 1:
            raise ValueError("min_orders должен быть больше нуля")
        if ranking_metric not in {
            "delayed_share",
            "delayed_orders",
            "average_delivery_days",
        }:
            raise ValueError(
                "ranking_metric должен быть delayed_share, delayed_orders "
                "или average_delivery_days"
            )
        if (
            start_date is not None
            and end_date is not None
            and end_date <= start_date
        ):
            raise ValueError("end_date должна быть позже start_date")

        return self.repository.get_region_delivery_ranking(
            limit=limit,
            min_orders=min_orders,
            ranking_metric=ranking_metric,
            start_date=start_date,
            end_date=end_date,
        )
