from django.urls import reverse
from core.roles import get_primary_role, Roles


def get_dashboard_url(user):

    if not user or not user.is_authenticated:
        return reverse("homepage")

    role = get_primary_role(user)

    route_map = {
        Roles.ADMIN: "admin_dashboard",
        Roles.HUB_PARTNER: "hub_dashboard",
        Roles.DELIVERY_BOY: "rider_dashboard",
    }

    return reverse(
        route_map.get(
            role,
            "where_we_deliver"
        )
    )