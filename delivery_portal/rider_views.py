from datetime import datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from admin_dashboard.models import CompanyInfo
from payments.models import FinancialWallet
from shop.models import Order

from .forms import ProofUploadForm
from .models import Delivery, DeliveryProfile, DeliveryStatus
from .utils import sync_order_status
from .views import delivery_boy_required


# =========================================================
# HELPERS
# =========================================================

def get_target_date(request):

    date_str = request.GET.get("date")

    try:

        if date_str:
            return datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

    except Exception:
        pass

    return timezone.localdate()


def get_day_bounds(date_obj):

    return (
        timezone.make_aware(
            datetime.combine(date_obj, time.min)
        ),
        timezone.make_aware(
            datetime.combine(date_obj, time.max)
        ),
    )


def serialize_delivery(delivery):

    order = delivery.order
    address = getattr(order, "address", None)
    hub = delivery.nearest_hub

    items = []

    try:
        for item in order.items.all():

            items.append({
                "name": getattr(item.product, "name", "Item"),
                "qty": item.quantity or 1,
                "size": getattr(item, "size", "") or "",
            })

    except Exception:
        pass

    return {

        # =====================================
        # BASIC
        # =====================================

        "id": delivery.id,

        "order_number": order.order_number or f"ORD-{delivery.id}",

        "status": delivery.status or "",

        "status_display": delivery.get_status_display() or "",

        # =====================================
        # MONEY
        # =====================================

        "earnings": float(
            delivery.rider_earning
            or delivery.delivery_fee
            or 0
        ),

        "cod_amount": float(
            order.total
            if getattr(delivery, "is_cod", False)
            else 0
        ),

        # =====================================
        # DELIVERY META
        # =====================================

        "distance_km": "2.5",

        "eta_minutes": "10",

        # =====================================
        # PICKUP
        # =====================================

        "pickup": {

            "hub_name": getattr(
                hub,
                "name",
                "Hub"
            ),

            "lat": float(
                getattr(hub, "latitude", 0)
                or 0
            ),

            "lng": float(
                getattr(hub, "longitude", 0)
                or 0
            ),
        },

        # =====================================
        # DROP
        # =====================================

        "drop": {

            "name": getattr(
                address,
                "recipient_name",
                "Customer"
            ),

            "phone": getattr(
                address,
                "phone_number",
                ""
            ),

            "city": getattr(
                address,
                "city",
                ""
            ),

            "full_address": getattr(
                address,
                "full_address",
                ""
            ),

            "landmark": getattr(
                address,
                "landmark",
                ""
            ),

            "lat": float(
                getattr(address, "latitude", 0)
                or 0
            ),

            "lng": float(
                getattr(address, "longitude", 0)
                or 0
            ),
        },

        # =====================================
        # ITEMS
        # =====================================

        "items": items,
    }



# =========================================================
# DASHBOARD
# =========================================================
from core.decorators import delivery_boy_required



from django.http import HttpResponse
import traceback

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
import traceback

from core.decorators import delivery_boy_required


@delivery_boy_required
def dashboard(request):
    """
    Rider Command Center

    - Safe for production
    - Never mixes list and QuerySet
    - Handles missing rider profile
    - Uses a single base queryset
    - Optimized with select_related/prefetch_related
    """

    steps = []

    try:
        steps.append("1. Dashboard entered")

        # --------------------------------------------------
        # Rider Profile
        # --------------------------------------------------

        try:
            profile = request.user.delivery_profile
        except Exception:
            messages.error(request, "Delivery profile not found.")
            return redirect("logout")

        steps.append("2. Delivery profile loaded")

        if not profile.hub:
            steps.append("3. No hub assigned")
            messages.error(request, "No delivery hub assigned.")
            return redirect("logout")

        steps.append("4. Hub OK")

        # --------------------------------------------------
        # Date
        # --------------------------------------------------

        target_date = get_target_date(request)
        start, end = get_day_bounds(target_date)

        steps.append("5. Date OK")

        # --------------------------------------------------
        # Base QuerySet
        # --------------------------------------------------

        base_qs = (
            Delivery.objects
            .select_related(
                "order",
                "order__address",
                "nearest_hub",
                "delivery_boy",
            )
            .prefetch_related(
                "order__items__product",
            )
        )

        steps.append("6. Base queryset OK")

        # --------------------------------------------------
        # Radar Orders
        # --------------------------------------------------

        radar_orders = base_qs.none()

        if profile.is_online:
            radar_orders = (
                base_qs.filter(
                    status=DeliveryStatus.PACKED,
                    delivery_boy__isnull=True,
                    nearest_hub_id=profile.hub_id,
                )
                .order_by("-created_at")
            )

        steps.append(f"7. Radar orders: {radar_orders.count()}")

        # --------------------------------------------------
        # Assigned
        # --------------------------------------------------

        assigned_orders = (
            base_qs.filter(
                delivery_boy=request.user,
                status=DeliveryStatus.ASSIGNED,
            )
            .order_by("-created_at")
        )

        steps.append(f"8. Assigned: {assigned_orders.count()}")

        # --------------------------------------------------
        # Out For Delivery
        # --------------------------------------------------

        out_orders = (
            base_qs.filter(
                delivery_boy=request.user,
                status=DeliveryStatus.OUT_FOR_DELIVERY,
            )
            .order_by("-created_at")
        )

        steps.append(f"9. Out for delivery: {out_orders.count()}")

        # --------------------------------------------------
        # Delivered Today
        # --------------------------------------------------

        delivered_orders = (
            base_qs.filter(
                delivery_boy=request.user,
                status=DeliveryStatus.DELIVERED,
                delivered_at__range=(start, end),
            )
        )

        steps.append(f"10. Delivered: {delivered_orders.count()}")

        # --------------------------------------------------
        # Earnings
        # --------------------------------------------------

        today_earnings = (
            delivered_orders.aggregate(
                total=Sum("rider_earning")
            )["total"] or 0
        )

        cash_in_hand = (
            delivered_orders.filter(
                cod_collected=True,
                cod_submitted=False,
            ).aggregate(
                total=Sum("cod_amount")
            )["total"] or 0
        )

        steps.append("11. Aggregates OK")

        # --------------------------------------------------
        # Wallet
        # --------------------------------------------------

        wallet, _ = FinancialWallet.objects.get_or_create(
            user=request.user
        )

        steps.append("12. Wallet OK")

        # --------------------------------------------------
        # Context
        # --------------------------------------------------

        context = {
            "company": CompanyInfo.objects.first(),
            "profile": profile,

            "orders": [
                serialize_delivery(d)
                for d in radar_orders
            ],

            "assigned": [
                serialize_delivery(d)
                for d in assigned_orders
            ],

            "out_deliveries": [
                serialize_delivery(d)
                for d in out_orders
            ],

            "today_earnings": float(today_earnings),
            "orders_delivered": delivered_orders.count(),
            "orders_cancelled": 0,
            "cash_to_pay": float(cash_in_hand),
            "wallet_balance": float(wallet.pending_balance or 0),
            "selected_date": target_date.isoformat(),
            "today": timezone.localdate().isoformat(),
        }

        steps.append("13. Context created")

        return render(
            request,
            "delivery_portal/dashboard.html",
            context,
        )

    except Exception:
        return HttpResponse(
            "<pre>"
            + "\n".join(steps)
            + "\n\n"
            + traceback.format_exc()
            + "</pre>"
        )

        
@login_required
@delivery_boy_required
def dashboard_api(request):

    profile = request.user.delivery_profile

    target_date = get_target_date(request)

    start, end = get_day_bounds(target_date)

    base_qs = (
        Delivery.objects
        .select_related(
            "order",
            "order__address",
            "nearest_hub",
            "delivery_boy"
        )
        .prefetch_related(
            "order__items__product"
        )
    )

    radar_orders = []

    if profile.is_online:

        radar_orders = base_qs.filter(
            status=DeliveryStatus.PACKED,
            delivery_boy__isnull=True,
            nearest_hub_id=profile.hub_id
        )

    assigned_orders = base_qs.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.ASSIGNED
    )

    out_orders = base_qs.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.OUT_FOR_DELIVERY
    )

    delivered_orders = base_qs.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.DELIVERED,
        delivered_at__range=(start, end)
    )

    earnings = delivered_orders.aggregate(
        total=Sum("rider_earning")
    )["total"] or 0

    cash = delivered_orders.filter(
        cod_collected=True
    ).aggregate(
        total=Sum("cod_amount")
    )["total"] or 0

    return JsonResponse({

        "orders": [
            serialize_delivery(d)
            for d in radar_orders
        ],

        "assigned": [
            serialize_delivery(d)
            for d in assigned_orders
        ],

        "out_deliveries": [
            serialize_delivery(d)
            for d in out_orders
        ],

        "today_earnings": float(earnings),

        "orders_delivered": delivered_orders.count(),

        "orders_cancelled": 0,

        "cash_to_pay": float(cash),
    })
# =========================================================
# ACCEPT ORDER
# =========================================================
@login_required
@delivery_boy_required
@transaction.atomic
def accept_order(request, delivery_id):

    if request.method != "POST":

        return JsonResponse(
            {
                "status": "error",
                "message": "POST required"
            },
            status=405
        )

    profile = request.user.delivery_profile

    if not profile.is_online:

        return JsonResponse(
            {
                "status": "error",
                "message": "You are offline"
            },
            status=400
        )

    try:

        delivery = (
            Delivery.objects
            .select_for_update(skip_locked=True)
            .select_related("order")
            .get(
                id=delivery_id,
                status=DeliveryStatus.PACKED,
                delivery_boy__isnull=True
            )
        )

    except Delivery.DoesNotExist:

        return JsonResponse(
            {
                "status": "error",
                "message": "Order already assigned"
            },
            status=404
        )

    # HUB VALIDATION

    if (
        profile.hub_id and
        delivery.nearest_hub_id != profile.hub_id
    ):

        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid hub assignment"
            },
            status=403
        )

    # ASSIGN

    delivery.delivery_boy = request.user

    delivery.status = DeliveryStatus.ASSIGNED

    delivery.assigned_at = timezone.now()

    delivery.save(
        update_fields=[
            "delivery_boy",
            "status",
            "assigned_at"
        ]
    )

    sync_order_status(
        delivery.order,
        DeliveryStatus.ASSIGNED
    )

    return JsonResponse({

        "status": "success",

        "message": "Order accepted",

        "delivery_id": delivery.id
    })



# =========================================================
# PICKUP CONFIRM
# =========================================================

@login_required
@delivery_boy_required
@transaction.atomic
def confirm_pickup(request, delivery_id):

    delivery = get_object_or_404(
        Delivery.objects.select_for_update(),
        pk=delivery_id,
        delivery_boy=request.user
    )

    if delivery.status != DeliveryStatus.ASSIGNED:

        messages.warning(
            request,
            "Invalid delivery state"
        )

        return redirect("rider_dashboard")

    delivery.status = DeliveryStatus.OUT_FOR_DELIVERY

    delivery.picked_from_hub_at = timezone.now()

    delivery.out_for_delivery_at = timezone.now()

    delivery.save(
        update_fields=[
            "status",
            "picked_from_hub_at",
            "out_for_delivery_at"
        ]
    )

    sync_order_status(
        delivery.order,
        DeliveryStatus.OUT_FOR_DELIVERY
    )

    messages.success(
        request,
        f"Pickup confirmed for #{delivery.order.order_number}"
    )

    return redirect("rider_dashboard")


# =========================================================
# COMPLETE DELIVERY
# =========================================================
from settlements.services import (create_order_settlements)
from payments.models import Payment

@login_required
@delivery_boy_required
@transaction.atomic
def complete_delivery(request, delivery_id):

    delivery = get_object_or_404(
        Delivery.objects
        .select_related("order"),
        pk=delivery_id,
        delivery_boy=request.user
    )

    order = delivery.order

    # =====================================================
    # VALIDATIONS
    # =====================================================

    if delivery.status != DeliveryStatus.OUT_FOR_DELIVERY:

        messages.error(
            request,
            "Delivery cannot be completed."
        )

        return redirect("rider_dashboard")

    if request.method == "POST":

        form = ProofUploadForm(
            request.POST,
            request.FILES,
            instance=delivery
        )

        entered_token = request.POST.get(
            "order_token",
            ""
        ).strip()

        cod_confirmed = request.POST.get(
            "cod_collected"
        ) == "yes"

        if entered_token != order.delivery_token:

            messages.error(
                request,
                "Invalid OTP"
            )

            return redirect(
                "complete_delivery",
                delivery_id=delivery.id
            )

        if form.is_valid():

            delivery = form.save(commit=False)

            # =============================================
            # OTP VERIFIED
            # =============================================

            delivery.otp_verified = True

            delivery.verified_at = timezone.now()

            # =============================================
            # COD HANDLING
            # =============================================

            if delivery.is_cod:

                if not cod_confirmed:

                    messages.error(
                        request,
                        "COD payment not confirmed."
                    )

                    return redirect(
                        "complete_delivery",
                        delivery_id=delivery.id
                    )

                delivery.cod_collected = True

                delivery.cod_collected_at = timezone.now()

                delivery.cod_amount = order.total

            # =============================================
            # DELIVERY COMPLETE
            # =============================================

            delivery.status = DeliveryStatus.DELIVERED

            delivery.delivered_at = timezone.now()

            delivery.save()

            # =============================================
            # WALLET UPDATE
            # =============================================

            wallet, _ = FinancialWallet.objects.get_or_create(
                user=request.user
            )

            wallet.pending_balance += (
                delivery.rider_earning or 0
            )

            if delivery.is_cod:

                wallet.cash_in_hand += order.total

            wallet.save()

            # =============================================
            # ORDER UPDATE
            # =============================================

            order.status = "delivered"

            order.save(
                update_fields=[
                    "status",
                    "delivered_at",
                    ]
            )

            # =============================================
            # PAYMENT UPDATE
            # =============================================

            payment = (
                order.payments
                .order_by("-created_at")
                .first()
            )

            if (payment and payment.status == "pending"and payment.method.name.lower() in ["cod", "upi"]):
                payment.status = "success"
                payment.paid_at = timezone.now()

                payment.save(
                    update_fields=[
                        "status",
                        "paid_at",
                    ]
                )
            
            create_order_settlements(order)

            sync_order_status(
                order,
                DeliveryStatus.DELIVERED
            )

            messages.success(
                request,
                f"Order #{order.order_number} delivered successfully"
            )

            return redirect("rider_dashboard")

    else:

        form = ProofUploadForm(
            instance=delivery
        )

    return render(
        request,
        "delivery_portal/complete_delivery.html",
        {
            "delivery": delivery,
            "form": form,
        }
    )


# =========================================================
# SUBMIT COD TO ADMIN
# =========================================================

@login_required
@delivery_boy_required
@transaction.atomic
def submit_cod(request):

    wallet, _ = FinancialWallet.objects.get_or_create(
        user=request.user
    )

    deliveries = Delivery.objects.filter(
        delivery_boy=request.user,
        cod_collected=True,
        cod_submitted=False,
        status=DeliveryStatus.DELIVERED
    )

    total_amount = deliveries.aggregate(
        total=Sum("cod_amount")
    )["total"] or 0

    if total_amount <= 0:

        messages.warning(
            request,
            "No COD amount pending."
        )

        return redirect("rider_dashboard")

    deliveries.update(
        cod_submitted=True,
        cod_submitted_at=timezone.now()
    )

    wallet.cash_in_hand -= total_amount

    if wallet.cash_in_hand < 0:
        wallet.cash_in_hand = 0

    wallet.save()

    messages.success(
        request,
        f"₹{total_amount} submitted successfully."
    )

    return redirect("rider_dashboard")