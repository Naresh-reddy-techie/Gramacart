import math
from .models import ShippingCost
from decimal import Decimal

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the Haversine distance between two lat/lng points.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in KM

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def get_rider_payout(hub, distance):
    """
    Finds the specific payout for a rider based on hub and distance.
    """
    pricing = ShippingCost.objects.filter(
        delivery_hub=hub,
        min_distance_km__lte=distance,
        max_distance_km__gte=distance
    ).first()
    
    # Fallback if no specific tier is found (e.g., very long distance)
    if not pricing:
        return Decimal('20.00') # Or your default base fare
    
    return pricing.rider_earning

from inventory.models import Inventory

def get_inventory(product, shop=None):
    """
    Always fetch inventory safely.
    If shop is not provided, you can pass default shop later.
    """
    return Inventory.objects.filter(product=product).first()