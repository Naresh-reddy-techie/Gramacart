from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from .models import Inventory, StockLog
from admin_dashboard.models import ShopLedger


# ============================================================
# INVENTORY TRANSACTION TYPES
# ============================================================

TRANSACTION_TYPES = [
    'RESTOCK',
    'SALE',

    'RETURN',
    'DAMAGED_RETURN',

    'WASTAGE',
    'EXPIRED',

    'TRANSFER_IN',
    'TRANSFER_OUT',
]


# ============================================================
# CENTRAL INVENTORY ENGINE
# ============================================================

@transaction.atomic
def adjust_inventory(
    *,
    inventory,
    quantity,
    transaction_type,
    note="",
    order=None,
    created_by=None
):

    """
    Central inventory transaction engine.

    quantity:
        +ve  => stock increase
        -ve  => stock decrease
    """

    if transaction_type not in TRANSACTION_TYPES:
        raise ValidationError("Invalid transaction type")

    if quantity == 0:
        raise ValidationError("Quantity cannot be zero")

    # Row locking (prevents race conditions)
    inventory = Inventory.objects.select_for_update().get(
        pk=inventory.pk
    )

    new_stock = inventory.stock + quantity

    if new_stock < 0:
        raise ValidationError(
            f"Insufficient stock for {inventory.variant}"
        )

    # Safe DB update
    inventory.stock = F('stock') + quantity
    inventory.save(update_fields=['stock'])

    # Refresh updated value
    inventory.refresh_from_db(fields=['stock'])

    # Audit Log
    StockLog.objects.create(
        inventory=inventory,
        change_amount=quantity,
        reason=transaction_type,
        note=note,
        order=order,
        created_by=created_by
    )

    return inventory


# ============================================================
# VALIDATE CART ITEM
# ============================================================

def validate_cart_item(variant, shop, qty):

    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero")

    try:
        inventory = Inventory.objects.get(
            variant=variant,
            shop=shop
        )

    except Inventory.DoesNotExist:

        raise ValidationError(
            f"{variant} not available in {shop.name}"
        )

    if inventory.stock <= 0:

        raise ValidationError(
            f"{variant} is out of stock"
        )

    if qty > inventory.available_for_order:

        raise ValidationError(
            f"Only {inventory.available_for_order} units available for {variant}"
        )

    return inventory


# ============================================================
# ORDER DELIVERY ENGINE
# ============================================================

@transaction.atomic
def handle_order_delivery(order):

    """
    Deduct stock + create ledger entries
    after successful order delivery.
    """

    if order.is_ledger_created:
        return

    if not order.shop or not order.hub:
        raise ValidationError(
            "Order must have assigned shop and hub"
        )

    items = order.items.select_related(
        'variant',
        'variant__product'
    )

    for item in items:

        try:
            inventory = Inventory.objects.select_for_update().get(
                variant=item.variant,
                shop=order.shop
            )

        except Inventory.DoesNotExist:

            raise ValidationError(
                f"{item.variant} unavailable in {order.shop.name}"
            )

        # Final stock validation
        if item.quantity > inventory.stock:

            raise ValidationError(
                f"Insufficient stock for {item.variant}"
            )

        # Safe stock deduction
        adjust_inventory(
            inventory=inventory,
            quantity=-item.quantity,
            transaction_type='SALE',
            note=f"Order #{order.order_number}",
            order=order
        )

        # Ledger creation
        ShopLedger.objects.create(
            shop=order.shop,
            hub=order.hub,
            order=order,
            inventory=inventory,
            quantity=item.quantity,
            cost_price=inventory.cost_price,
            selling_price=inventory.selling_price
        )

    order.is_ledger_created = True

    order.save(
        update_fields=['is_ledger_created']
    )


# ============================================================
# RESTOCK INVENTORY
# ============================================================

@transaction.atomic
def restock_inventory(
    *,
    variant,
    shop,
    qty,
    cost_price=None,
    selling_price=None,
    note="Manual Restock",
    created_by=None
):

    if qty <= 0:
        raise ValidationError(
            "Restock quantity must be positive"
        )

    inventory, created = Inventory.objects.select_for_update().get_or_create(
        variant=variant,
        shop=shop,
        defaults={
            "stock": 0,
            "cost_price": cost_price or 0,
            "selling_price": selling_price or 0,
        }
    )

    # Optional price updates
    if cost_price is not None:
        inventory.cost_price = cost_price

    if selling_price is not None:
        inventory.selling_price = selling_price

    inventory.save()

    adjust_inventory(
        inventory=inventory,
        quantity=qty,
        transaction_type='RESTOCK',
        note=note,
        created_by=created_by
    )

    return inventory


# ============================================================
# DAMAGE / WASTAGE
# ============================================================

@transaction.atomic
def mark_inventory_wastage(
    *,
    inventory,
    qty,
    reason='WASTAGE',
    note='',
    created_by=None
):

    if qty <= 0:
        raise ValidationError(
            "Quantity must be positive"
        )

    adjust_inventory(
        inventory=inventory,
        quantity=-qty,
        transaction_type=reason,
        note=note,
        created_by=created_by
    )

    return inventory


# ============================================================
# CUSTOMER RETURN
# ============================================================

@transaction.atomic
def process_customer_return(
    *,
    inventory,
    qty,
    reusable=True,
    note='Customer Return',
    created_by=None
):

    if qty <= 0:
        raise ValidationError(
            "Quantity must be positive"
        )

    # Reusable item → add stock back
    if reusable:

        adjust_inventory(
            inventory=inventory,
            quantity=qty,
            transaction_type='RETURN',
            note=note,
            created_by=created_by
        )

    # Damaged item → no reusable stock
    else:

        adjust_inventory(
            inventory=inventory,
            quantity=-qty,
            transaction_type='DAMAGED_RETURN',
            note=note,
            created_by=created_by
        )

    return inventory


# ============================================================
# SAFE INVENTORY FETCH
# ============================================================

def get_inventory(variant, shop):

    try:

        return Inventory.objects.select_related(
            'variant',
            'variant__product',
            'shop'
        ).get(
            variant=variant,
            shop=shop
        )

    except Inventory.DoesNotExist:
        return None


# ============================================================
# AUTO SHOP ASSIGNMENT ENGINE
# ============================================================

def assign_shop_to_order(order):

    """
    Finds the first active shop
    that can fulfill the complete order.
    """

    items = order.items.select_related(
        'variant',
        'variant__product'
    )

    candidate_shops = order.hub.shops.filter(
        is_active=True
    )

    for shop in candidate_shops:

        can_fulfill = True

        for item in items:

            exists = Inventory.objects.filter(
                variant=item.variant,
                shop=shop,
                stock__gte=item.quantity
            ).exists()

            if not exists:
                can_fulfill = False
                break

        if can_fulfill:

            order.shop = shop

            order.save(
                update_fields=['shop']
            )

            return shop

    raise ValidationError(
        "No shop can fulfill this order"
    )


# ============================================================
# FUTURE: SHOP TO SHOP TRANSFER
# ============================================================

@transaction.atomic
def transfer_inventory(
    *,
    variant,
    from_shop,
    to_shop,
    qty,
    note=""
):

    if qty <= 0:
        raise ValidationError(
            "Transfer quantity must be positive"
        )

    try:
        source_inventory = Inventory.objects.select_for_update().get(
            variant=variant,
            shop=from_shop
        )

    except Inventory.DoesNotExist:

        raise ValidationError(
            "Source inventory not found"
        )

    destination_inventory, created = Inventory.objects.select_for_update().get_or_create(
        variant=variant,
        shop=to_shop,
        defaults={
            "stock": 0,
            "cost_price": source_inventory.cost_price,
            "selling_price": source_inventory.selling_price,
        }
    )

    # Remove from source
    adjust_inventory(
        inventory=source_inventory,
        quantity=-qty,
        transaction_type='TRANSFER_OUT',
        note=note
    )

    # Add to destination
    adjust_inventory(
        inventory=destination_inventory,
        quantity=qty,
        transaction_type='TRANSFER_IN',
        note=note
    )

    return destination_inventory