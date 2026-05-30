from geopy.distance import geodesic
from admin_dashboard.models import DeliveryHub


def resolve_user_hub(lat: float, lon: float):
    """
    Always returns nearest hub from user GPS.
    """

    hubs = DeliveryHub.objects.filter(
        is_active=True,
        is_accepting_orders=True
    )

    nearest = None
    min_dist = float("inf")

    for hub in hubs:
        if not hub.latitude or not hub.longitude:
            continue

        dist = geodesic(
            (lat, lon),
            (float(hub.latitude), float(hub.longitude))
        ).meters

        if dist < min_dist:
            min_dist = dist
            nearest = hub

    return nearest


def set_user_location_session(request, lat, lon, hub):
    """
    ONLY stores data. NO decision making.
    """

    request.session["user_lat"] = lat
    request.session["user_lon"] = lon

    if hub:
        request.session["hub_id"] = hub.id
        request.session["hub_lat"] = float(hub.latitude)
        request.session["hub_lon"] = float(hub.longitude)


def get_session_hub(request):
    hub_id = request.session.get("hub_id")

    if hub_id:
        return DeliveryHub.objects.filter(id=hub_id).first()

    return None


def get_fallback_hub():
    return DeliveryHub.objects.filter(
        is_active=True,
        is_accepting_orders=True
    ).first()