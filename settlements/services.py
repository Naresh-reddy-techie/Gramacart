from django.db import transaction

from .models import (
    ShopSettlement,
    ShopWallet
)


@transaction.atomic
def create_order_settlements(order):

    if order.is_ledger_created:
        return

    for item in order.items.select_related(
        "inventory",
        "inventory__shop"
    ):

        inventory = item.inventory

        if not inventory:
            continue

        shop = inventory.shop

        # Skip GramaCart-owned shops
        if shop.is_internal:
            continue

        settlement, created = (
            ShopSettlement.objects.get_or_create(
                order_item=item,
                shop=shop,
                defaults={
                    "hub": shop.hub,
                    "quantity": item.quantity,
                    "gross_amount": (
                        item.price * item.quantity
                    ),
                    "commission_percent": (
                        shop.commission_percent
                    ),
                }
            )
        )

        if created:

            wallet, _ = (
                ShopWallet.objects.get_or_create(
                    shop=shop
                )
            )

            wallet.pending_balance += (
                settlement.net_amount
            )

            wallet.save(
                update_fields=[
                    "pending_balance",
                    "updated_at"
                ]
            )

    order.is_ledger_created = True

    order.save(
        update_fields=[
            "is_ledger_created"
        ]
    )



from django.db import transaction
from django.utils import timezone

from .models import (
    ShopWallet,
    ShopSettlement,
    ShopPayout
)


from django.db import transaction
from django.utils import timezone

from .models import (
    ShopWallet,
    ShopSettlement,
    ShopPayout
)


@transaction.atomic
def process_shop_payout(
    shop,
    amount,
    reference_number,
    paid_by,
    remarks=""
):

    wallet = ShopWallet.objects.select_for_update().get(
        shop=shop
    )

    if amount <= 0:
        raise ValueError(
            "Amount must be greater than zero"
        )

    if amount > wallet.pending_balance:
        raise ValueError(
            "Cannot pay more than pending balance"
        )

    payout = ShopPayout.objects.create(
        shop=shop,
        wallet=wallet,
        amount=amount,
        reference_number=reference_number,
        remarks=remarks,
        paid_by=paid_by,
        status="SUCCESS"
    )

    # ===================================
    # UPDATE WALLET
    # ===================================

    wallet.pending_balance -= amount
    wallet.total_paid += amount

    wallet.save(
        update_fields=[
            "pending_balance",
            "total_paid",
            "updated_at"
        ]
    )

    # ===================================
    # MARK SETTLEMENTS PAID
    # ===================================

    ShopSettlement.objects.filter(
        shop=shop,
        status="PENDING"
    ).update(
        status="PAID",
        paid_at=timezone.now()
    )

    return payout