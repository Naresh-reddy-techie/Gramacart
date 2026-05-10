import logging
import requests
from decimal import Decimal, ROUND_HALF_UP
from collections import namedtuple
from typing import Optional, Dict, Any, Tuple

from django.conf import settings
from geopy.distance import geodesic

# Use absolute imports based on your project structure
from admin_dashboard.models import DeliveryHub, ShippingCost

logger = logging.getLogger(__name__)

# Professional-grade return structure
HubCheck = namedtuple('HubCheck', ['deliverable', 'distance_km', 'nearest_hub'])

# ----------------------------------------------------------------
# Distance & Deliverability Logic
# ----------------------------------------------------------------

def check_address_within_hub(address: Any, allow_remote: bool = False) -> HubCheck:
    """
    Determines if an address is within a service zone or marked as remote.
    """
    if not address or not address.latitude or not address.longitude:
        return HubCheck(deliverable=allow_remote, distance_km=None, nearest_hub=None)

    try:
        address_coord = (float(address.latitude), float(address.longitude))
    except (ValueError, TypeError):
        return HubCheck(deliverable=allow_remote, distance_km=None, nearest_hub=None)

    min_distance = None
    nearest_hub = None
    is_within_radius = False

    # Fetch active hubs once to save DB hits
    active_hubs = DeliveryHub.objects.filter(is_active=True)
    
    for hub in active_hubs:
        hub_coord = (hub.latitude, hub.longitude)
        # geodesic is accurate for India's curvature
        distance = geodesic(address_coord, hub_coord).km
        
        if min_distance is None or distance < min_distance:
            min_distance = distance
            nearest_hub = hub
            
        if distance <= float(hub.max_delivery_radius_km):
            is_within_radius = True

    # Logic: It's deliverable if it's within a hub radius OR the user explicitly opted for remote delivery
    deliverable = is_within_radius or allow_remote

    return HubCheck(
        deliverable=deliverable,
        distance_km=Decimal(str(round(min_distance, 2))) if min_distance is not None else None,
        nearest_hub=nearest_hub
    )

# ----------------------------------------------------------------
# Shipping Cost Calculation
# ----------------------------------------------------------------

def calculate_shipping_cost(address: Any) -> Dict[str, Any]:
    """
    Calculates costs based on distance slabs or remote surcharges.
    """
    # Safety check: does the address model have an is_remote field?
    is_remote_flag = getattr(address, 'is_remote', False)
    hub_info = check_address_within_hub(address, allow_remote=is_remote_flag)
    
    # Default fail state
    res = {
        'customer_fee': Decimal('0.00'),
        'rider_earning': Decimal('0.00'),
        'platform_fee': Decimal('0.00'),
        'distance_km': hub_info.distance_km or Decimal('0.00'),
        'hub_name': hub_info.nearest_hub.name if hub_info.nearest_hub else "Unknown",
        'error': True,
        'is_remote': is_remote_flag
    }

    if not hub_info.deliverable or not hub_info.nearest_hub:
        return res

    # Find the matching slab for the specific hub
    shipping = ShippingCost.objects.filter(
        delivery_hub=hub_info.nearest_hub,
        min_distance_km__lte=float(hub_info.distance_km),
        max_distance_km__gte=float(hub_info.distance_km)
    ).first()

    if shipping:
        res.update({
            'customer_fee': Decimal(str(shipping.cost)),
            'rider_earning': Decimal(str(shipping.rider_earning)),
            'platform_fee': Decimal(str(shipping.platform_fee)),
            'error': False
        })
    # elif is_remote_flag:
    #     # VILLAGE-SPECIFIC: If no slab matches but it's a remote order, use a flat fallback fee
    #     # You can adjust these defaults or pull from a settings model later
    #     res.update({
    #         'customer_fee': Decimal('60.00'), 
    #         'rider_earning': Decimal('45.00'),
    #         'platform_fee': Decimal('15.00'),
    #         'error': False
    #     })
        
    return res

# ----------------------------------------------------------------
# Order Totals Engine
# ----------------------------------------------------------------

def calculate_order_totals(cart_items: Any, address: Any = None, discount_percent: Decimal = 0) -> Dict[str, Decimal]:
    """
    Main engine to calculate final amounts for checkout.
    """
    # 1. Base Subtotal
    sub_total = sum(
        (Decimal(str(item.quantity)) * Decimal(str(item.product.price))) 
        for item in cart_items
    )

    # 2. Shipping Calculation
    shipping_fee = Decimal('0.00')
    if address:
        shipping_res = calculate_shipping_cost(address)
        if not shipping_res['error']:
            shipping_fee = shipping_res['customer_fee']

    # 3. Discount (Applied to subtotal only)
    discount_amount = (Decimal(str(discount_percent)) / 100) * sub_total

    # 4. Final Calculation
    # Note: In hyper-local models, tax is usually inclusive in product price.
    # If exclusive, calculate it here: (sub_total - discount_amount) * tax_rate
    final_total = (sub_total - discount_amount) + shipping_fee

    # Rounding function for currency display
    def clean(val): return val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxes = Decimal('0.00')
    return {
        "sub_total": clean(sub_total),
        "shipping_cost": clean(shipping_fee),
        "discount_amount": clean(discount_amount),
        "taxes": clean(taxes),  
        "final_total": clean(final_total),
    }

# ----------------------------------------------------------------
# External Geocoding (Safe & Bound)
# ----------------------------------------------------------------

def get_lat_long_from_address(address_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetches coordinates with India-specific boundary constraints.
    """
    if not address_text:
        return None, None

    url = "https://us1.locationiq.com/v1/search.php"
    params = {
        'key': settings.LOCATIONIQ_ACCESS_TOKEN,
        'q': address_text,
        'format': 'json',
        'limit': 1,
        'countrycodes': 'in'  # Strictly India for GramaCart/Buride
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data[0]['lat']), float(data[0]['lon'])
        
        logger.warning(f"Geocoding status {response.status_code} for: {address_text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during geocoding: {e}")
    
    return None, None