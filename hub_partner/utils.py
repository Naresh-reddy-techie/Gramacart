from django.shortcuts import get_object_or_404
from admin_dashboard.models import DeliveryHub


def get_current_hub(request):
    hub_id = request.session.get("active_hub_id")

    if hub_id:
        return DeliveryHub.objects.filter(
            id=hub_id,
            owner=request.user,
            is_active=True
        ).first()

    return request.user.owned_hubs.filter(
        is_active=True
    ).first()


def get_user_hubs(user):
    """
    Returns all hubs owned by the logged-in partner.
    """
    return user.owned_hubs.filter(
        is_active=True
    )


def get_hub_for_user(user, hub_id):
    """
    Security check:
    Ensures the requested hub belongs to the logged-in user.
    """

    return get_object_or_404(
        DeliveryHub,
        id=hub_id,
        owner=user,
        is_active=True
    )