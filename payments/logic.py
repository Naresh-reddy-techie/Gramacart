from admin_dashboard.models import ShippingCost
from decimal import Decimal


def apply_shipping_rates(delivery_obj):
    """
    Finds the correct pricing from your ShippingCost model 
    based on the distance from the Hub to the Customer.
    """
    # 1. Look for a matching distance slab in your model
    rate_card = ShippingCost.objects.filter(
        delivery_hub=delivery_obj.nearest_hub,
        min_distance_km__lte=delivery_obj.distance_km,
        max_distance_km__gte=delivery_obj.distance_km
    ).first()

    if rate_card:
        # 2. 'Freeze' these values into the individual Delivery record
        # This ensures if you change the Master Price later, 
        # this old delivery pay doesn't change.
        delivery_obj.delivery_fee = rate_card.cost
        delivery_obj.rider_earning = rate_card.rider_earning
        delivery_obj.platform_fee = rate_card.platform_fee
        delivery_obj.save()

"""
from payments.models import FinancialWallet
from django.db import transaction
def settle_order_funds(delivery):
    
    # Triggers when status becomes 'DELIVERED'.
    # Distributes money to Rider and Shopkeeper using your Admin models.
   
    order = delivery.order
    
    with transaction.atomic():
        # 1. UPDATE RIDER WALLET
        # We use the 'rider_earning' you defined in your ShippingCost model
        rider_wallet, _ = FinancialWallet.objects.get_or_create(user=delivery.delivery_boy)
        rider_wallet.pending_balance += delivery.rider_earning 
        
        # If it's COD, the rider is now 'carrying' your cash
        if order.payments.filter(method__name__iexact='cod').exists():
            rider_wallet.cash_in_hand += order.total
        
        rider_wallet.save()

        # 2. UPDATE SHOPKEEPER WALLET
        # We use the 'cost_price' you added to the Product model
        total_vendor_cost = Decimal('0.00')
        for item in order.items.all():
            total_vendor_cost += item.product.cost_price * item.quantity
        
        # Find the shopkeeper (Assuming Order -> Vendor/Shop relation)
        vendor_wallet, _ = FinancialWallet.objects.get_or_create(user=order.vendor.user)
        vendor_wallet.pending_balance += total_vendor_cost
        vendor_wallet.save()

"""

# payments/logic.py
from payments.models import FinancialWallet
from django.db import transaction
from decimal import Decimal

def settle_order_funds(delivery):
    """
    Triggers when status becomes 'DELIVERED'.
    Currently only distributes money to the Rider.
    """
    order = delivery.order
    
    with transaction.atomic():
        # 1. UPDATE RIDER WALLET
        # This pays the rider their delivery fee
        rider_wallet, _ = FinancialWallet.objects.get_or_create(user=delivery.delivery_boy)
        
        # Add the rider's specific earning for this trip
        rider_wallet.pending_balance += delivery.rider_earning 
        
        # 2. HANDLE CASH ON DELIVERY (COD)
        # If the rider collected cash from the customer, track it here
        if order.payments.filter(method__name__iexact='cod').exists():
            # Using 'total' as per your Order model
            rider_wallet.cash_in_hand += order.total 
        
        rider_wallet.save()

        # Note: Shopkeeper/Vendor logic removed until you create the Vendor app.