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