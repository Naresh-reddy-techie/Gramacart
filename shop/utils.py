import math
import time
import requests
import logging
from decimal import Decimal, ROUND_HALF_UP
from collections import namedtuple
from geopy.distance import geodesic

from django.conf import settings
from admin_dashboard.models import DeliveryHub, ShippingCost

logger = logging.getLogger(__name__)

HubCheck = namedtuple('HubCheck', ['deliverable', 'distance_km', 'nearest_hub'])

# ------------------ Distance & Deliverability ------------------

def check_address_within_hub(address, allow_remote=False):
    """
    Check if an address is deliverable and return nearest hub & distance.
    Uses geopy for professional-grade accuracy.
    """
    if not address or not address.latitude or not address.longitude:
        return HubCheck(deliverable=allow_remote, distance_km=None, nearest_hub=None)

    address_coord = (float(address.latitude), float(address.longitude))
    min_distance = None
    nearest_hub = None
    deliverable = False

    # Only check hubs that are currently operational
    hubs = DeliveryHub.objects.filter(is_active=True)
    
    for hub in hubs:
        hub_coord = (hub.latitude, hub.longitude)
        distance = geodesic(address_coord, hub_coord).km
        
        if min_distance is None or distance < min_distance:
            min_distance = distance
            nearest_hub = hub
            
        if distance <= hub.max_delivery_radius_km:
            deliverable = True

    if not deliverable and allow_remote:
        deliverable = True

    return HubCheck(
        deliverable=deliverable,
        distance_km=Decimal(str(min_distance)) if min_distance is not None else None,
        nearest_hub=nearest_hub
    )

# ------------------ Shipping Cost Calculation ------------------
def calculate_shipping_cost(address):
    hub_info = check_address_within_hub(address)
    
    # Define a safe default response
    default_response = {
        'customer_fee': Decimal('0'),
        'rider_earning': Decimal('0'),
        'platform_fee': Decimal('0'),
        'distance_km': hub_info.distance_km or 0,
        'hub_name': hub_info.nearest_hub.name if hub_info.nearest_hub else "Unknown",
        'error': True
    }

    if not hub_info.deliverable or not hub_info.nearest_hub:
        return default_response

    # Search for the slab
    shipping = ShippingCost.objects.filter(
        delivery_hub=hub_info.nearest_hub,
        min_distance_km__lte=float(hub_info.distance_km),
        max_distance_km__gte=float(hub_info.distance_km)
    ).first()

    if not shipping:
        # If distance is 7.2km and your max slab is 7.0km, it hits here
        return default_response

    return {
        'customer_fee': Decimal(str(shipping.cost or 0)),
        'rider_earning': Decimal(str(shipping.rider_earning or 0)),
        'platform_fee': Decimal(str(shipping.platform_fee or 0)),
        'distance_km': hub_info.distance_km,
        'hub_name': hub_info.nearest_hub.name,
        'error': False
    }

# ------------------ Order Totals Calculation ------------------

def calculate_order_totals(cart_items, address=None, discount_percentage=0, tax_percentage=0):
    """Main calculation engine for the checkout page."""
    
    # Subtotal
    sub_total = sum(Decimal(str(item.quantity)) * Decimal(str(item.product.price)) for item in cart_items)

    # Shipping
    shipping_cost = Decimal('0')
    if address:
        res = calculate_shipping_cost(address)
        if not res['error']:
            shipping_cost = res['customer_fee']

    # Math
    discount = (Decimal(str(discount_percentage)) / 100) * sub_total
    # Tax is usually calculated on (Subtotal - Discount)
    taxable_amount = sub_total - discount + shipping_cost
    taxes = (Decimal(str(tax_percentage)) / 100) * taxable_amount
    
    final_total = taxable_amount + taxes

    # Rounding Helper
    def fmt(val): return val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "sub_total": fmt(sub_total),
        "shipping_cost": fmt(shipping_cost),
        "discount": fmt(discount),
        "taxes": fmt(taxes),
        "final_total": fmt(final_total),
    }

# ------------------ Geocoding ------------------

def get_lat_long_from_address(address_text):
    """Fetch coordinates from LocationIQ."""
    url = "https://us1.locationiq.com/v1/search.php"
    params = {'key': settings.LOCATIONIQ_ACCESS_TOKEN, 'q': address_text, 'format': 'json', 'limit': 1}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
    
    return None, None