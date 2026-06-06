from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from core.decorators import hub_partner_required

from .forms import HubShippingCostForm
from admin_dashboard.models import (
    HubPartnerProfile,
    ShippingCost,
)


# =========================================================
# HUB HELPER
# SINGLE SOURCE OF TRUTH
# =========================================================

def get_partner_hub(user):

    partner = get_object_or_404(
        HubPartnerProfile.objects.select_related("hub"),
        user=user
    )

    return partner, partner.hub


# =========================================================
# SHIPPING COST LIST
# =========================================================

@hub_partner_required
def shipping_cost_list(request):

    partner, hub = get_partner_hub(
        request.user
    )

    shipping_costs = (
        ShippingCost.objects
        .filter(
            delivery_hub=hub
        )
        .order_by(
            "min_distance_km"
        )
    )

    context = {
        "partner": partner,
        "hub": hub,
        "shipping_costs": shipping_costs,
    }

    return render(
        request,
        "hub_dashboard/shipping/shipping_cost_list.html",
        context
    )


# =========================================================
# ADD SHIPPING COST
# =========================================================

@hub_partner_required
def add_shipping_cost(request):

    partner, hub = get_partner_hub(
        request.user
    )

    if request.method == "POST":

        form = HubShippingCostForm(
            request.POST
        )

        if form.is_valid():

            shipping = form.save(
                commit=False
            )

            # FORCE HUB OWNERSHIP
            shipping.delivery_hub = hub

            shipping.save()

            messages.success(
                request,
                "Shipping slab added successfully."
            )

            return redirect(
                "hub_shipping_cost_list"
            )

    else:

        form = HubShippingCostForm()

    context = {
        "partner": partner,
        "hub": hub,
        "form": form,
        "page_title": "Add Shipping Slab",
    }

    return render(
        request,
        "hub_dashboard/shipping/shipping_cost_form.html",
        context
    )


# =========================================================
# EDIT SHIPPING COST
# =========================================================

@hub_partner_required
def edit_shipping_cost(request, pk):

    partner, hub = get_partner_hub(
        request.user
    )

    shipping = get_object_or_404(
        ShippingCost,
        pk=pk,
        delivery_hub=hub
    )

    if request.method == "POST":

        form = HubShippingCostForm(
            request.POST,
            instance=shipping
        )

        if form.is_valid():

            shipping_obj = form.save(
                commit=False
            )

            # NEVER ALLOW HUB CHANGE
            shipping_obj.delivery_hub = hub

            shipping_obj.save()

            messages.success(
                request,
                "Shipping slab updated successfully."
            )

            return redirect(
                "hub_shipping_cost_list"
            )

    else:

        form = HubShippingCostForm(
            instance=shipping
        )

    context = {
        "partner": partner,
        "hub": hub,
        "form": form,
        "shipping": shipping,
        "page_title": "Update Shipping Slab",
    }

    return render(
        request,
        "hub_dashboard/shipping/shipping_cost_form.html",
        context
    )


# =========================================================
# DELETE SHIPPING COST
# =========================================================

@hub_partner_required
def delete_shipping_cost(request, pk):

    partner, hub = get_partner_hub(
        request.user
    )

    shipping = get_object_or_404(
        ShippingCost,
        pk=pk,
        delivery_hub=hub
    )

    if request.method == "POST":

        shipping.delete()

        messages.success(
            request,
            "Shipping slab deleted successfully."
        )

        return redirect(
            "hub_shipping_cost_list"
        )

    context = {
        "partner": partner,
        "hub": hub,
        "shipping": shipping,
    }

    return render(
        request,
        "hub_dashboard/shipping/delete.html",
        context
    )