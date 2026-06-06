from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta

from shop.models import Order


class HubOrderService:

    STATUS_PIPELINE = {
        "new": ["pending"],
        "packed": ["packed"],
        "assigned": ["assigned"],
        "out_for_delivery": ["out_for_delivery"],
        "delivered": ["delivered"],
        "cancelled": ["cancelled", "declined"],
    }

    @staticmethod
    def get_base_queryset(hub):
        return Order.objects.filter(hub=hub).select_related(
            "user", "address", "hub"
        ).prefetch_related(
            "items__product__product_images"
        )

    @staticmethod
    def apply_time_filter(qs, time_filter):

        now = timezone.now()

        if time_filter in ["day", "today"]:
            start = timezone.make_aware(
                timezone.datetime.combine(
                    timezone.localdate(),
                    timezone.datetime.min.time()
                )
            )
            end = timezone.make_aware(
                timezone.datetime.combine(
                    timezone.localdate(),
                    timezone.datetime.max.time()
                )
            )
            return qs.filter(placed_at__range=(start, end))

        if time_filter == "week":
            return qs.filter(placed_at__gte=now - timedelta(days=7))

        if time_filter == "month":
            return qs.filter(placed_at__gte=now - timedelta(days=30))

        return qs

    @staticmethod
    def apply_filters(qs, status, search):

        if status in HubOrderService.STATUS_PIPELINE:
            qs = qs.filter(status__in=HubOrderService.STATUS_PIPELINE[status])
        else:
            qs = qs.filter(status="pending")

        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(user__username__icontains=search) |
                Q(address__phone_number__icontains=search)
            )

        return qs.order_by("-placed_at")

    @staticmethod
    def get_metrics(qs):

        return {
            "new_orders": qs.filter(status__in=["pending"]).count(),
            "packed_orders": qs.filter(status="packed").count(),
            "assigned_orders": qs.filter(status="assigned").count(),
            "out_orders": qs.filter(status="out_for_delivery").count(),
            "delivered_orders": qs.filter(status="delivered").count(),
            "cancelled_orders": qs.filter(status__in=["cancelled", "declined"]).count(),
            "revenue": qs.filter(status="delivered").aggregate(
                total=Sum("total")
            )["total"] or 0
        }