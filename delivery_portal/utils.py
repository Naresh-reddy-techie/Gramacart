import logging
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from decimal import Decimal
from .models import Delivery, DeliveryProfile, DeliveryStatus
from admin_dashboard.models import ShippingCost
from shop.utils import check_address_within_hub

logger = logging.getLogger(__name__)

# ------------------- 1. Geography & Pricing -------------------

def get_shipping_slab(hub, distance_km):
    return ShippingCost.objects.filter(
        delivery_hub=hub,
        min_distance_km__lte=distance_km,
        max_distance_km__gte=distance_km
    ).first()

# ------------------- 2. Delivery Processing Logic -------------------
def prepare_delivery_for_radar(delivery_id):

    try:

        with transaction.atomic():

            delivery = (
                Delivery.objects
                .select_for_update()
                .select_related("order__address")
                .get(pk=delivery_id)
            )

            if delivery.delivery_boy:
                return False

            order = delivery.order

            if not order.address:
                logger.error(
                    f"Delivery {delivery_id} missing address."
                )
                return False

            # ==========================================
            # HUB RESOLUTION
            # ==========================================

            loc_data = check_address_within_hub(
                order.address
            )

            if not loc_data.deliverable:
                logger.warning(
                    f"Address not deliverable for "
                    f"Order #{order.order_number}"
                )
                return False

            hub = loc_data.delivery_hub

            distance = (
                loc_data.distance_km or Decimal("0.00")
            )

            if not hub:
                logger.warning(
                    f"No hub found for "
                    f"Order #{order.order_number}"
                )
                return False

            # ==========================================
            # SHIPPING SLAB
            # ==========================================

            slab = get_shipping_slab(
                hub,
                distance
            )

            if not slab:

                logger.error(
                    f"No slab found for "
                    f"{distance}km at {hub.name}"
                )

                return False

            # ==========================================
            # FREEZE DELIVERY DATA
            # ==========================================

            delivery.nearest_hub = hub

            delivery.distance_km = distance

            delivery.delivery_fee = slab.cost

            delivery.rider_earning = slab.rider_earning

            delivery.platform_fee = slab.platform_fee

            delivery.status = DeliveryStatus.PACKED

            delivery.save()

            # ==========================================
            # ORDER STATUS
            # ==========================================

            sync_order_status(
                order,
                DeliveryStatus.PACKED
            )

            logger.info(
                f"Delivery #{delivery.id} "
                f"ready for rider radar."
            )

            return True

    except Exception as e:

        logger.exception(
            f"Radar preparation failed: {str(e)}"
        )

        return False

def manual_assign_rider(delivery_id, rider_user):
    """
    Bypasses Radar. Admin directly assigns a specific rider.
    """
    try:
        with transaction.atomic():
            delivery = Delivery.objects.select_for_update().get(pk=delivery_id)
            delivery.delivery_boy = rider_user
            delivery.status = DeliveryStatus.ASSIGNED
            delivery.assigned_at = timezone.now()
            delivery.save()
            
            sync_order_status(delivery.order, DeliveryStatus.ASSIGNED)
            return True
    except Exception as e:
        logger.error(f"Manual Assignment Failure: {str(e)}")
        return False

# ------------------- 3. Orchestration -------------------

def create_delivery_record(order):
    """
    Entry point: Creates the initial record in PENDING.
    """
    return Delivery.objects.create(
        order=order,
        status=DeliveryStatus.PENDING
    )

def sync_order_status(order, delivery_status):
    """
    Updates the main Order status to reflect Delivery progress.
    """
    mapping = {
        DeliveryStatus.PENDING: 'pending',
        DeliveryStatus.PACKED: 'packed',
        DeliveryStatus.ASSIGNED: 'assigned', 
        DeliveryStatus.OUT_FOR_DELIVERY: 'out_for_delivery',
        DeliveryStatus.DELIVERED: 'delivered',
        DeliveryStatus.CANCELLED: 'cancelled',
    }
    new_status = mapping.get(delivery_status)
    if new_status and order.status != new_status:
        order.status = new_status
        order.save(update_fields=['status'])