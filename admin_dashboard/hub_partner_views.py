from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.models import User, Group
from django.db import transaction
from django.contrib import messages


from admin_dashboard.forms import (HubPartnerForm,HubSubscriptionForm,HubUserCreateForm)

from admin_dashboard.models import (HubPartnerProfile,HubSubscription)


from django.shortcuts import render, get_object_or_404




@login_required
def hub_partner_list(request):

    partners = (HubPartnerProfile.objects.select_related("user","hub").all().order_by("-created_at"))

    return render(request,"admin_dashboard/hub_partners/hub_partner_list.html",{"partners": partners})


from datetime import date, timedelta
from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group

@login_required
def add_hub_partner(request):

    user_form = HubUserCreateForm(request.POST or None)
    profile_form = HubPartnerForm(request.POST or None)
    subscription_form = HubSubscriptionForm(request.POST or None)

    if request.method == "POST":

        if user_form.is_valid() and profile_form.is_valid() and subscription_form.is_valid():

            try:
                with transaction.atomic():

                    username = user_form.cleaned_data["username"]
                    password = user_form.cleaned_data["password"]

                    if User.objects.filter(username=username).exists():
                        user_form.add_error("username", "Username already exists")
                        raise ValueError("Username exists")

                    user = User.objects.create_user(username=username, password=password)

                    group, _ = Group.objects.get_or_create(name="HubPartner")
                    user.groups.add(group)

                    partner = profile_form.save(commit=False)
                    partner.user = user
                    partner.save()

                    subscription = subscription_form.save(commit=False)
                    subscription.partner = partner
                    start_date = subscription_form.cleaned_data.get("start_date")

                    if not start_date:
                        start_date = date.today()

                    subscription.start_date = start_date
                    subscription.end_date =start_date + timedelta(days=365)

                    subscription.save()

                    messages.success(request, "Hub Partner created successfully")
                    return redirect("hub_partner_list")

            except Exception as e:
                messages.error(request, str(e))

    return render(request, "admin_dashboard/hub_partners/add_hub_partner.html", {
        "user_form": user_form,
        "profile_form": profile_form,
        "subscription_form": subscription_form,
    })
@login_required
def edit_hub_partner(request,partner_id):

    partner = get_object_or_404(HubPartnerProfile,id=partner_id)

    subscription = get_object_or_404(HubSubscription,partner=partner)

    if request.method == "POST":

        profile_form = HubPartnerForm(request.POST,instance=partner)
        subscription_form = HubSubscriptionForm(request.POST,instance=subscription)

        if (profile_form.is_valid()and subscription_form.is_valid()):

            profile_form.save()
            subscription_form.save()

            messages.success(request,"Partner updated successfully.")
            return redirect("hub_partner_list")
    else:
        profile_form = HubPartnerForm(instance=partner)
        subscription_form = HubSubscriptionForm(instance=subscription)

    return render(request,"admin_dashboard/hub_partners/edit_hub_partner.html",
    {"profile_form": profile_form,"subscription_form": subscription_form,"partner": partner,})



@login_required
def toggle_hub_partner_status(request, partner_id):

    partner = get_object_or_404(HubPartnerProfile,id=partner_id)

    partner.is_active = not partner.is_active
    partner.save(update_fields=["is_active"])

    partner.user.is_active = partner.is_active
    partner.user.save(update_fields=["is_active"])

    if partner.is_active:

        messages.success(request,f"{partner.hub.name} partner activated successfully.")
    else:

        messages.warning(request,f"{partner.hub.name} partner deactivated successfully.")

    return redirect("hub_partner_list")


@login_required
def hub_partner_detail(request, partner_id):

    partner = get_object_or_404(HubPartnerProfile.objects.select_related("user","hub"),id=partner_id)

    subscription = HubSubscription.objects.filter(partner=partner).first()

    context = {
        "partner": partner,
        "subscription": subscription,
    }

    return render(request,"admin_dashboard/hub_partners/hub_partner_detail.html",context)


#==============================================================

