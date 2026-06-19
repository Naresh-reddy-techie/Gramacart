from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from django.contrib import messages
from shop.models import Order
from delivery_portal.models import DeliveryProfile
from admin_dashboard.models import HubPartnerProfile
from core.decorators import hub_partner_required

from .services.orders import HubOrderService
from .utils import get_current_hub

@hub_partner_required
def hub_dashboard(request):

    hub = get_current_hub(request)
    if not hub:
        messages.error(request,"No hub assigned")
        return redirect('logout')

    partner = getattr(request.user,"hub_partner_profile",None)
    hub = partner.hub
    today = now().date()

    # BASE HUB ORDERS
    base_orders = HubOrderService.get_base_queryset(hub)

    # KPI SAFE (using correct field: placed_at)
    orders_today = base_orders.filter(
        placed_at__date=today
    ).count()

    pending_orders = base_orders.filter(
        status="pending"
    ).count()

    delivered_today = base_orders.filter(
        status="delivered",
        updated_at__date=today
    ).count()

    active_riders = DeliveryProfile.objects.filter(
        hub=hub,
        is_active=True
    ).count()

    context = {
        "partner": partner,
        "hub": hub,
        "orders_today": orders_today,
        "pending_orders": pending_orders,
        "delivered_today": delivered_today,
        "active_riders": active_riders,
    }

    return render(request, "hub_dashboard/dashboard.html", context)


from django.shortcuts import redirect, get_object_or_404
from admin_dashboard.models import DeliveryHub


@hub_partner_required
def switch_hub(request, hub_id):

    hub = get_object_or_404(
        DeliveryHub,
        id=hub_id,
        owner=request.user
    )

    request.session["active_hub_id"] = hub.id

    return redirect("hub_dashboard")




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from shop.models import Order
from admin_dashboard.models import HubPartnerProfile
from core.decorators import hub_partner_required

from .services.orders import HubOrderService

def serialize_order(order):

    return {
        "order_number": order.order_number,

        "status": order.status,
        "status_label": order.display_status,
        "status_code": order.status,

        "customer": (
            order.address.recipient_name
            if order.address
            else order.user.username
        ),

        "phone": (
            order.address.phone_number
            if order.address
            else None
        ),

        "address": (
            order.address.full_address
            if order.address
            else ""
        ),

        "hub": (
            order.hub.name
            if order.hub
            else ""
        ),

        "subtotal": float(order.subtotal),
        "tax": float(order.tax),
        "shipping_cost": float(order.shipping_cost),
        "total": float(order.total),

        "eta_minutes": order.estimated_eta_minutes,
        "distance_km": float(
            order.estimated_distance_km or 0
        ),

        "created_at": order.placed_at.strftime(
            "%d %b %Y %H:%M"
        ),

        # =====================================
        # ACTION FLAGS
        # =====================================

        "can_pack": order.status == "pending",

        "can_assign": order.status == "packed",

        "can_cancel": order.status in [
            "pending",
            "packed",
            "assigned",
        ],

        "can_view": True,

        # =====================================

        "items": [
            {
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.price),
            }
            for item in order.items.all()
        ]
    }


@hub_partner_required
def hub_orders_json(request):

    partner = get_object_or_404(
        HubPartnerProfile.objects.select_related("hub"),
        user=request.user
    )

    hub = partner.hub

    qs = HubOrderService.get_base_queryset(hub)

    # filters
    status = request.GET.get("status", "pending")
    search = request.GET.get("search", "")
    time_filter = request.GET.get("time", "day")

    qs = HubOrderService.apply_time_filter(qs, time_filter)
    qs = HubOrderService.apply_filters(qs, status, search)

    orders = [serialize_order(o) for o in qs[:50]]

    metrics = HubOrderService.get_metrics(qs)

    return JsonResponse({
        "orders": orders,
        "metrics": metrics
    })


@hub_partner_required
def hub_orders(request):

    partner = get_object_or_404(
        HubPartnerProfile.objects.select_related("hub", "user"),
        user=request.user
    )

    hub = partner.hub

    context = {
        "partner": partner,
        "hub": hub,
    }

    return render(request, "hub_dashboard/orders.html", context)


#==========================================================
