from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import MarketplaceSettingsForm
from .models import MarketplaceSettings


@login_required
def marketplace_settings(request):
    """
    Create or update the global marketplace configuration.
    """

    marketplace_settings, created = MarketplaceSettings.objects.get_or_create(
        pk=1,
        defaults={
            "marketplace_open": True,
            "free_delivery_enabled": True,
            "free_delivery_min_order": 999,
            "cod_enabled": True,
        },
    )

    if request.method == "POST":

        form = MarketplaceSettingsForm(
            request.POST,
            instance=marketplace_settings
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Marketplace configuration has been updated successfully."
            )

            return redirect("marketplace_settings")

    else:

        form = MarketplaceSettingsForm(
            instance=marketplace_settings
        )

    context = {
        "form": form,
        "marketplace_settings": marketplace_settings,
    }

    return render(
        request,
        "admin_dashboard/marketplace_settings.html",
        context,
    )