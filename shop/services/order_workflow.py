from django.db import transaction

from shop.models import Order
from shop.utils import get_route_data

from delivery_portal.models import (
    Delivery,
    DeliveryProfile
)

from delivery_portal.utils import (
    prepare_delivery_for_radar
)

from admin_dashboard.services.order_service import (
    OrderService
)


class OrderWorkflowService:
    """
    =====================================================
    SINGLE SOURCE OF TRUTH
    =====================================================

    Used By:
    - Super Admin
    - Hub Partner
    - Future Hub Manager
    - Operations Team
    - APIs

    NEVER change order status directly in views.
    Always call this service.
    """

    # =====================================================
    # PACK ORDER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def mark_packed(order):

        if order.status != "pending":
            raise ValueError(
                "Only pending orders can be packed."
            )

        order.status = "packed"

        order.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        delivery, created = Delivery.objects.get_or_create(
            order=order
        )

        success = prepare_delivery_for_radar(
            delivery.id
        )

        if not success:
            raise ValueError(
                "Delivery radar preparation failed."
            )

        return order

    # =====================================================
    # ASSIGN RIDER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_rider(
        order,
        rider_profile: DeliveryProfile
    ):

        if order.status != "packed":
            raise ValueError(
                "Order must be packed before assigning rider."
            )

        delivery = OrderService.assign_rider(
            order,
            rider_profile
        )

        route_data = None

        try:

            start_lat = order.hub.latitude
            start_lng = order.hub.longitude

            end_lat = order.address.latitude
            end_lng = order.address.longitude

            route_data = get_route_data(
                start_lat=start_lat,
                start_lng=start_lng,
                end_lat=end_lat,
                end_lng=end_lng
            )

        except Exception:
            pass

        order.status = "assigned"

        if route_data:

            order.estimated_distance_km = (
                route_data["distance_km"]
            )

            order.estimated_eta_minutes = (
                route_data["eta_minutes"]
            )

        order.save(
            update_fields=[
                "status",
                "estimated_distance_km",
                "estimated_eta_minutes",
                "updated_at"
            ]
        )

        return delivery

    # =====================================================
    # START DELIVERY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def start_delivery(order):

        if order.status != "assigned":
            raise ValueError(
                "Order must be assigned first."
            )

        order.status = "out_for_delivery"

        order.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        return order

    # =====================================================
    # DELIVER ORDER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def mark_delivered(order):

        if order.status != "out_for_delivery":
            raise ValueError(
                "Order is not out for delivery."
            )

        order.status = "delivered"

        order.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        return order

    # =====================================================
    # REJECT ORDER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def reject_order(
        order,
        reason=""
    ):

        if order.status in [
            "delivered",
            "cancelled",
            "declined"
        ]:
            raise ValueError(
                "Order cannot be rejected."
            )

        order.status = "declined"

        order.rejection_reason = (
            reason or "No reason provided"
        )

        order.save(
            update_fields=[
                "status",
                "rejection_reason",
                "updated_at"
            ]
        )

        return order

    # =====================================================
    # CANCEL ORDER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def cancel_order(
        order,
        reason=""
    ):

        if order.status == "delivered":
            raise ValueError(
                "Delivered orders cannot be cancelled."
            )

        order.status = "cancelled"

        order.rejection_reason = (
            reason or "Cancelled"
        )

        order.save(
            update_fields=[
                "status",
                "rejection_reason",
                "updated_at"
            ]
        )

        return order