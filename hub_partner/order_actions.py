# hub_partner/order_actions.py

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core.decorators import hub_partner_required

from shop.models import Order
from delivery_portal.models import DeliveryProfile
from admin_dashboard.models import HubPartnerProfile

from shop.services.order_workflow import OrderWorkflowService

# =========================================================

# HUB HELPERS

# =========================================================

def get_partner_hub(user):


    partner = get_object_or_404(
        HubPartnerProfile.objects.select_related("hub"),
        user=user
    )

    return partner.hub


from .utils import get_current_hub

def get_hub_order(request, order_number):

    hub = get_current_hub(request)

    return get_object_or_404(
        Order.objects.select_related(
            "hub",
            "shop",
            "user",
            "address"
        ),
        order_number=order_number,
        hub=hub
    )

def parse_json_request(request):

    try:

        return json.loads(request.body)

    except (json.JSONDecodeError, TypeError):

        return None


# =========================================================

# MARK ORDER AS PACKED

# =========================================================

@hub_partner_required
@require_POST
def mark_order_as_packed(request, order_number):

    order = get_hub_order(
        request.user,
        order_number
    )

    try:

        OrderWorkflowService.mark_packed(
            order,
            actor=request.user
        )

        return JsonResponse({
            "success": True,
            "message": "Order packed successfully."
        })

    except ValueError as e:

        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Unable to process request."
        }, status=500)


# =========================================================

# REJECT ORDER

# =========================================================

@hub_partner_required
@require_POST
def reject_order(request):

    data = parse_json_request(request)

    if not data:

        return JsonResponse({
            "success": False,
            "message": "Invalid request payload."
        }, status=400)

    order = get_hub_order(
        request.user,
        data.get("order_number")
    )

    reason = data.get(
        "reason",
        "No reason provided"
    )

    try:

        OrderWorkflowService.reject_order(
            order,
            reason,
            actor=request.user
        )

        return JsonResponse({
            "success": True,
            "message": "Order rejected successfully."
        })

    except ValueError as e:

        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Unable to process request."
        }, status=500)


# =========================================================

# ASSIGN RIDER

# =========================================================

@hub_partner_required
@require_POST
def assign_rider(request):

    data = parse_json_request(request)

    if not data:

        return JsonResponse({
            "success": False,
            "message": "Invalid request payload."
        }, status=400)

    hub = get_partner_hub(
        request.user
    )

    order = get_hub_order(
        request.user,
        data.get("order_number")
    )

    rider = get_object_or_404(
        DeliveryProfile.objects.select_related(
            "user",
            "hub"
        ),
        id=data.get("delivery_boy_id"),
        hub=hub
    )

    try:

        delivery = OrderWorkflowService.assign_rider(
            order,
            rider,
            actor=request.user
        )

        return JsonResponse({

            "success": True,
            "message": "Rider assigned successfully.",

            "earning": float(
                delivery.rider_earning
            ),

            "eta_minutes": (
                order.estimated_eta_minutes
            ),

            "distance_km": float(
                order.estimated_distance_km or 0
            )

        })

    except ValueError as e:

        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Unable to process request."
        }, status=500)

