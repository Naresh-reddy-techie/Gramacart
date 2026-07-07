import logging
from decimal import Decimal, ROUND_HALF_UP
from collections import namedtuple
from typing import Any, Dict, Optional, Tuple

import requests

from django.conf import settings

from geopy.distance import geodesic

from admin_dashboard.models import (
    DeliveryHub,
    ShippingCost,
    MarketplaceSettings,
)

logger = logging.getLogger(__name__)

# =========================================================
# RESPONSE STRUCTURE
# =========================================================

HubCheck = namedtuple(
    "HubCheck",
    [
        "deliverable",
        "distance_km",
        "delivery_hub"
    ]
)

# =========================================================
# HUB RESOLUTION ENGINE
# =========================================================

def get_nearest_hub(
    latitude: float,
    longitude: float
) -> Tuple[Optional[DeliveryHub], Optional[float]]:

    """
    Finds nearest active delivery hub.
    """

    hubs = DeliveryHub.objects.filter(
        is_active=True,
        is_accepting_orders=True
    )

    nearest_hub = None
    minimum_distance = float("inf")

    customer_point = (
        float(latitude),
        float(longitude)
    )

    for hub in hubs:

        if hub.latitude is None or hub.longitude is None:
            continue

        hub_point = (
            float(hub.latitude),
            float(hub.longitude)
        )

        distance_km = geodesic(
            customer_point,
            hub_point
        ).km

        if distance_km < minimum_distance:
            minimum_distance = distance_km
            nearest_hub = hub

    return nearest_hub, minimum_distance


# =========================================================
# DELIVERY RADIUS VALIDATION
# =========================================================

def is_within_delivery_radius(
    address,
    hub
) -> bool:

    """
    Final security gate.
    Prevents ordering outside hub radius.
    """

    if not address or not hub:
        return False

    if address.latitude is None or address.longitude is None:
        return False

    if hub.latitude is None or hub.longitude is None:
        return False

    customer_point = (
        float(address.latitude),
        float(address.longitude)
    )

    hub_point = (
        float(hub.latitude),
        float(hub.longitude)
    )

    distance_km = geodesic(
        customer_point,
        hub_point
    ).km

    return distance_km <= float(hub.max_delivery_radius_km)


# =========================================================
# ADDRESS HUB CHECK
# =========================================================

def check_address_within_hub(
    address: Any,
    allow_remote: bool = False
) -> HubCheck:

    """
    Dynamically resolves nearest hub from GPS.
    """

    latitude = getattr(address, "latitude", None)
    longitude = getattr(address, "longitude", None)

    if latitude is None or longitude is None:

        return HubCheck(
            deliverable=False,
            distance_km=None,
            delivery_hub=None
        )

    hub, distance_km = get_nearest_hub(
        latitude,
        longitude
    )

    if not hub:

        return HubCheck(
            deliverable=False,
            distance_km=None,
            delivery_hub=None
        )

    distance_decimal = Decimal(str(distance_km))

    within_radius = (
        distance_decimal <=
        Decimal(str(hub.max_delivery_radius_km))
    )

    return HubCheck(
        deliverable=within_radius or allow_remote,
        distance_km=distance_decimal,
        delivery_hub=hub
    )


# =========================================================
# SHIPPING ENGINE
# =========================================================

def calculate_shipping_cost(
    address: Any,
    delivery_hub=None
) -> Dict[str, Any]:

    """
    Centralized shipping engine.
    """

    response = {

        "customer_fee": Decimal("0.00"),

        "rider_earning": Decimal("0.00"),

        "platform_fee": Decimal("0.00"),

        "distance_km": Decimal("0.00"),

        "hub_name": None,

        "delivery_hub": None,

        "error": True,

        "message": "Delivery unavailable"
    }

    # =====================================================
    # HUB VALIDATION
    # =====================================================

    if not delivery_hub:

        response["message"] = "Delivery hub missing"

        return response

    # =====================================================
    # SECURITY VALIDATION
    # =====================================================

    if not is_within_delivery_radius(
        address,
        delivery_hub
    ):

        response["message"] = (
            "Address outside delivery area"
        )

        return response

    # =====================================================
    # DISTANCE CALCULATION
    # =====================================================

    customer_point = (
        float(address.latitude),
        float(address.longitude)
    )

    hub_point = (
        float(delivery_hub.latitude),
        float(delivery_hub.longitude)
    )

    distance_km = geodesic(
        customer_point,
        hub_point
    ).km

    distance_decimal = Decimal(
        str(distance_km)
    ).quantize(
        Decimal("0.01")
    )

    response.update({

        "distance_km": distance_decimal,

        "hub_name": delivery_hub.name,

        "delivery_hub": delivery_hub
    })

    # =====================================================
    # SHIPPING SLAB
    # =====================================================

    shipping_slab = ShippingCost.objects.filter(

        delivery_hub=delivery_hub,

        min_distance_km__lte=float(distance_decimal),

        max_distance_km__gte=float(distance_decimal)

    ).order_by(
        "min_distance_km"
    ).first()

    if not shipping_slab:

        response["message"] = (
            f"No shipping slab configured for "
            f"{distance_decimal} km"
        )

        return response

    # =====================================================
    # SUCCESS
    # =====================================================

    response.update({

        "customer_fee": Decimal(
            str(shipping_slab.cost)
        ),

        "rider_earning": Decimal(
            str(shipping_slab.rider_earning)
        ),

        "platform_fee": Decimal(
            str(shipping_slab.platform_fee)
        ),

        "error": False,

        "message": "Success"
    })

    return response


# for market place


from decimal import Decimal
from typing import Dict, Any


def calculate_final_shipping(
    subtotal: Decimal,
    address,
    delivery_hub,
) -> Dict[str, Any]:
    """
    Calculate the final shipping payable by the customer after applying
    marketplace-wide delivery rules.

    Responsibilities:
        1. Calculate shipping from distance.
        2. Apply marketplace policies (Free Delivery etc.).
        3. Return a complete shipping response.
    """

    shipping_data = calculate_shipping_cost(
        address=address,
        delivery_hub=delivery_hub,
    )

    # Delivery unavailable
    if shipping_data["error"]:
        return shipping_data

    original_shipping_fee = Decimal(
        str(shipping_data["customer_fee"])
    )

    marketplace_settings = MarketplaceSettings.objects.first()

    # Default response
    shipping_data.update({
        "original_shipping_fee": original_shipping_fee,
        "free_delivery": False,
        "free_delivery_threshold": None,
        "remaining_for_free_delivery": Decimal("0.00"),
        "delivery_message": "",
    })

    # No configuration found
    if not marketplace_settings:
        return shipping_data

    threshold = marketplace_settings.free_delivery_min_order

    shipping_data["free_delivery_threshold"] = threshold

    # Eligible for free delivery
    if (
        marketplace_settings.free_delivery_enabled
        and subtotal >= threshold
    ):
        shipping_data["customer_fee"] = Decimal("0.00")
        shipping_data["free_delivery"] = True
        shipping_data["remaining_for_free_delivery"] = Decimal("0.00")
        shipping_data["delivery_message"] = (
            "Congratulations! You have unlocked FREE delivery."
        )

    else:

        remaining = max(
            Decimal("0.00"),
            threshold - subtotal
        )

        shipping_data["remaining_for_free_delivery"] = remaining

        shipping_data["delivery_message"] = (
            f"Add ₹{remaining:.2f} more to unlock FREE delivery."
        )

    return shipping_data


# =========================================================
# ORDER TOTALS ENGINE
# =========================================================

def calculate_order_totals(
    cart_items,
    address=None,
    delivery_hub=None,
    discount_percent=Decimal("0")
):

    sub_total = sum(

        Decimal(str(item.unit_price or 0)) *
        item.quantity

        for item in cart_items
    )

    shipping_fee = Decimal("0.00")

    if address and delivery_hub:

        shipping_data = calculate_shipping_cost(
            address=address,
            delivery_hub=delivery_hub
        )

        if not shipping_data["error"]:
            shipping_fee = shipping_data["customer_fee"]

    discount_amount = (
        Decimal(str(discount_percent)) / 100
    ) * sub_total

    final_total = (
        sub_total -
        discount_amount +
        shipping_fee
    )

    def clean(value):
        return value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    return {

        "sub_total": clean(sub_total),

        "shipping_cost": clean(shipping_fee),

        "discount_amount": clean(discount_amount),

        "taxes": Decimal("0.00"),

        "final_total": clean(final_total)
    }


# =========================================================
# GEOCODING ENGINE
# =========================================================

def get_lat_long_from_address(
    address_text: str
) -> Tuple[Optional[float], Optional[float]]:

    """
    India-focused geocoder.
    """

    if not address_text:
        return None, None

    url = "https://us1.locationiq.com/v1/search.php"

    params = {

        "key": settings.LOCATIONIQ_ACCESS_TOKEN,

        "q": address_text,

        "format": "json",

        "limit": 1,

        "countrycodes": "in"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=5
        )

        if response.status_code == 200:

            data = response.json()

            return (

                float(data[0]["lat"]),

                float(data[0]["lon"])
            )

        logger.warning(
            f"Geocoding failed: {response.status_code}"
        )

    except requests.exceptions.RequestException as e:

        logger.error(
            f"Geocoding network error: {e}"
        )

    return None, None

#==========================================
import requests
from django.conf import settings

LOCATIONIQ_API_KEY = settings.LOCATIONIQ_ACCESS_TOKEN


def get_route_data(start_lat, start_lng, end_lat, end_lng):

    """
    Returns:
    {
        "distance_km": float,
        "eta_minutes": int
    }
    """

    try:

        url = (
            "https://us1.locationiq.com/v1/directions/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}"
        )

        params = {
            "key": LOCATIONIQ_API_KEY,
            "overview": "false",
            "steps": "false",
            "geometries": "geojson",
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if "routes" not in data:
            return None

        route = data["routes"][0]

        distance_km = round(
            route["distance"] / 1000,
            2
        )

        eta_minutes = max(
            1,
            round(route["duration"] / 60)
        )

        return {
            "distance_km": distance_km,
            "eta_minutes": eta_minutes
        }

    except requests.RequestException:
        return None

    except Exception:
        return None