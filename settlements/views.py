from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required


from .models import (
    ShopSettlement,
    ShopWallet
)


@login_required
def shop_settlement_list(request):

    settlements = (
        ShopSettlement.objects
        .select_related(
            "shop",
            "hub",
            "order_item__order"
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "settlements/shop_settlement_list.html",
        {
            "settlements": settlements
        }
    )


@login_required
def shop_wallet_list(request):

    wallets = (
        ShopWallet.objects
        .select_related("shop")
        .order_by("shop__name")
    )

    return render(
        request,
        "settlements/shop_wallet_list.html",
        {
            "wallets": wallets
        }
    )


from django.shortcuts import (
    render,
    get_object_or_404
)

from .models import (
    ShopWallet,
    ShopSettlement
)


@login_required
def shop_wallet_detail(request, wallet_id):

    wallet = get_object_or_404(
        ShopWallet.objects.select_related(
            "shop"
        ),
        pk=wallet_id
    )

    settlements = (
        ShopSettlement.objects
        .filter(
            shop=wallet.shop
        )
        .select_related(
            "order_item__order"
        )
        .order_by("-created_at")
    )

    context = {
        "wallet": wallet,
        "settlements": settlements,
    }

    return render(
        request,
        "settlements/shop_wallet_detail.html",
        context
    )


from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from .forms import ShopPayoutForm
from .models import ShopWallet
from .services import process_shop_payout

@login_required
def shop_wallet_pay(request, wallet_id):

    wallet = get_object_or_404(
        ShopWallet.objects.select_related(
            "shop"
        ),
        pk=wallet_id
    )

    if request.method == "POST":

        form = ShopPayoutForm(request.POST)

        if form.is_valid():

            try:

                process_shop_payout(

                    shop=wallet.shop,

                    amount=form.cleaned_data["amount"],

                    reference_number=form.cleaned_data[
                        "reference_number"
                    ],

                    paid_by=request.user,

                    remarks=form.cleaned_data[
                        "remarks"
                    ]

                )

                messages.success(
                    request,
                    "Payout processed successfully."
                )

                return redirect(
                    "shop_wallet_detail",
                    wallet_id=wallet.id
                )

            except Exception as e:

                messages.error(
                    request,
                    str(e)
                )

    else:

        form = ShopPayoutForm(
            initial={
                "amount": wallet.pending_balance
            }
        )

    context = {

        "wallet": wallet,

        "form": form,

    }

    return render(
        request,
        "settlements/shop_wallet_pay.html",
        context
    )