from django.shortcuts import get_object_or_404,render,redirect
from admin_dashboard.models import HubPartnerProfile
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.models import Group,User

# =========================================================
# HUB HELPER
# =========================================================

def get_partner_hub(user):

    partner = get_object_or_404(
        HubPartnerProfile.objects.select_related("hub"),
        user=user
    )

    return partner.hub


from core.decorators import hub_partner_required
from delivery_portal.models import DeliveryProfile


from django.shortcuts import render

from core.decorators import hub_partner_required

from delivery_portal.models import (
    DeliveryProfile,
    Delivery,
    DeliveryStatus
)




@hub_partner_required
def rider_list(request):

    hub = get_partner_hub(
        request.user
    )

    riders = DeliveryProfile.objects.select_related(
        "user",
        "hub"
    ).filter(
        hub=hub
    ).order_by(
        "user__first_name"
    )

    busy_ids = Delivery.objects.filter(
        status__in=[
            DeliveryStatus.ASSIGNED,
            DeliveryStatus.OUT_FOR_DELIVERY
        ]
    ).values_list(
        "delivery_boy_id",
        flat=True
    )

    total_riders = riders.count()

    active_riders = riders.filter(
        is_active=True
    ).count()

    busy_riders = riders.filter(
        user_id__in=busy_ids
    ).count()

    offline_riders = riders.filter(
        is_active=False
    ).count()

    context = {

        "riders": riders,

        "total_riders": total_riders,

        "active_riders": active_riders,

        "busy_riders": busy_riders,

        "offline_riders": offline_riders,

        "busy_ids": list(busy_ids)

    }

    return render(
        request,
        "hub_dashboard/riders/rider_list.html",
        context
    )





# =========================================================
# ADD RIDER
# =========================================================

@hub_partner_required
def add_rider(request):

    hub = get_partner_hub(
        request.user
    )

    if request.method == "POST":

        try:

            username = request.POST.get(
                "username"
            ).strip()

            password = request.POST.get(
                "password"
            ).strip()

            first_name = request.POST.get(
                "first_name"
            ).strip()

            last_name = request.POST.get(
                "last_name"
            ).strip()

            phone_number = request.POST.get(
                "phone_number"
            ).strip()

            vehicle_type = request.POST.get(
                "vehicle_type",
                "bike"
            )

            is_active = (
                request.POST.get(
                    "is_active"
                ) == "on"
            )

            # =====================================
            # VALIDATIONS
            # =====================================

            if User.objects.filter(
                username=username
            ).exists():

                messages.error(
                    request,
                    "Username already exists."
                )

                return redirect(
                    "hub_add_rider"
                )

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )

                group, _ = Group.objects.get_or_create(
                    name="DeliveryBoy"
                )

                user.groups.add(
                    group
                )

                DeliveryProfile.objects.create(

                    user=user,

                    hub=hub,

                    phone_number=phone_number,

                    vehicle_type=vehicle_type,

                    is_active=is_active
                )

            messages.success(
                request,
                f"Rider {username} created successfully."
            )

            return redirect(
                "hub_rider_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    context = {

        "hub": hub,

        "vehicle_choices": DeliveryProfile.VEHICLE_CHOICES

    }

    return render(
        request,
        "hub_dashboard/riders/add_rider.html",
        context
    )

@hub_partner_required
def edit_rider(request, rider_id):

    hub = get_partner_hub(
        request.user
    )

    rider = get_object_or_404(
        DeliveryProfile,
        id=rider_id,
        hub=hub
    )

    if request.method == "POST":

        rider.user.first_name = request.POST.get(
            "first_name"
        )

        rider.user.last_name = request.POST.get(
            "last_name"
        )

        rider.user.save()

        rider.is_active = (
            request.POST.get("is_active")
            == "on"
        )

        rider.save()

        messages.success(
            request,
            "Rider updated."
        )

        return redirect(
            "hub_rider_list"
        )

    return render(
        request,
        "hub_dashboard/riders/edit_rider.html",
        {
            "rider": rider
        }
    )

@hub_partner_required
def toggle_rider_status(
    request,
    rider_id
):

    hub = get_partner_hub(
        request.user
    )

    rider = get_object_or_404(
        DeliveryProfile,
        id=rider_id,
        hub=hub
    )

    rider.is_active = (
        not rider.is_active
    )

    rider.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        "Status updated."
    )

    return redirect(
        "hub_rider_list"
    )

@hub_partner_required
def reset_rider_password(
    request,
    rider_id
):

    hub = get_partner_hub(
        request.user
    )

    rider = get_object_or_404(
        DeliveryProfile,
        id=rider_id,
        hub=hub
    )

    if request.method == "POST":

        password = request.POST.get(
            "password"
        )

        rider.user.set_password(
            password
        )

        rider.user.save()

        messages.success(
            request,
            "Password reset."
        )

        return redirect(
            "hub_rider_list"
        )

    return render(
        request,
        "hub_dashboard/riders/reset_password.html",
        {
            "rider": rider
        }
    )