from django.db import models
from payments.utils import generate_upi_qr_code

class PaymentMethod(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g. 'paypal', 'cod'
    display_name = models.CharField(max_length=100)      # e.g. 'Cash on Delivery'
    is_active = models.BooleanField(default=True)
    config = models.JSONField(blank=True, null=True)     # Dynamic settings (API keys, etc.)
    sort_order = models.IntegerField(default=0)          # Optional: display order in UI

    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        # If this is a UPI payment and qr_code is not set, generate it
        if self.name.lower() == 'upi' and self.config:
            upi_id = self.config.get('upi_id')
            payee_name = self.config.get('payee_name')  # Optional
            if upi_id and not self.qr_code:
                qr_image = generate_upi_qr_code(upi_id, payee_name)
                self.qr_code.save(f'{self.name}_upi_qr.png', qr_image, save=False)
        
        super().save(*args, **kwargs)



class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey("shop.Order", on_delete=models.CASCADE, related_name="payments")
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')

    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True,null=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.method.name} - {self.status}"

    @property
    def is_paid(self):
        return self.status == "success"


    @property
    def is_pending(self):
        return self.status == "pending"


    @property
    def is_failed(self):
        return self.status == "failed"


    @property
    def is_refunded(self):
        return self.status == "refunded"



class FinancialWallet(models.Model):
    """The 'Account Balance' for each Rider or Shopkeeper."""
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name='wallet')
    
    # Money GramaCart owes them (Commissions or Product Cost)
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # (For Riders) Cash they collected from customers but haven't given to Admin yet
    cash_in_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Wallet | Balance: ₹{self.pending_balance}"

class Payout(models.Model):
    """Record of Admin actually paying the Rider/Vendor (Settlement)."""
    wallet = models.ForeignKey(FinancialWallet, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=100, help_text="UPI Transaction ID or 'CASH'")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payout of ₹{self.amount} to {self.wallet.user.username}"