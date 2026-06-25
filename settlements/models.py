from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone


class ShopSettlement(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    # =====================================================
    # RELATIONS
    # =====================================================

    order_item = models.ForeignKey(
        'shop.OrderItem',
        on_delete=models.CASCADE,
        related_name='settlements'
    )

    shop = models.ForeignKey(
        'admin_dashboard.Shop',
        on_delete=models.CASCADE,
        related_name='settlements',
        db_index=True
    )

    hub = models.ForeignKey(
        'admin_dashboard.DeliveryHub',
        on_delete=models.CASCADE,
        related_name='settlements',
        db_index=True
    )

    # =====================================================
    # SNAPSHOT DATA
    # Stored permanently for accounting history
    # =====================================================

    quantity = models.PositiveIntegerField()

    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Customer paid amount for this order item."
    )

    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Commission percentage at settlement creation time."
    )

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount payable to the shop."
    )

    # =====================================================
    # SETTLEMENT STATUS
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['shop', 'status']),
            models.Index(fields=['hub', 'status']),
            models.Index(fields=['created_at']),
        ]

        constraints = [

            models.UniqueConstraint(
                fields=['order_item', 'shop'],
                name='unique_orderitem_shop_settlement'
            ),

            models.CheckConstraint(
                condition=Q(
                    commission_percent__gte=0
                ),
                name='settlement_commission_gte_zero'
            ),

            models.CheckConstraint(
                condition=Q(
                    commission_percent__lte=100
                ),
                name='settlement_commission_lte_hundred'
            ),

        ]

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):

        super().clean()

        if self.quantity <= 0:
            raise ValidationError(
                "Quantity must be greater than zero."
            )

        if self.gross_amount < 0:
            raise ValidationError(
                "Gross amount cannot be negative."
            )

        if self.commission_percent < 0:
            raise ValidationError(
                "Commission cannot be negative."
            )

        if self.commission_percent > 100:
            raise ValidationError(
                "Commission cannot exceed 100%."
            )

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        self.full_clean()

        self.commission_amount = (
            Decimal(self.gross_amount)
            * Decimal(self.commission_percent)
        ) / Decimal("100")

        self.net_amount = (
            Decimal(self.gross_amount)
            - self.commission_amount
        )

        super().save(*args, **kwargs)

    # =====================================================
    # HELPERS
    # =====================================================

    @property
    def order(self):
        return self.order_item.order

    @property
    def is_paid(self):
        return self.status == 'PAID'

    @property
    def payout_amount(self):
        return self.net_amount

    # =====================================================
    # ACTIONS
    # =====================================================

    def mark_paid(self):

        if self.status == 'PAID':
            return

        self.status = 'PAID'
        self.paid_at = timezone.now()

        self.save(
            update_fields=[
                'status',
                'paid_at',
                'updated_at'
            ]
        )

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.shop.name} | "
            f"{self.net_amount} | "
            f"{self.status}"
        )
    

class ShopWallet(models.Model):

    shop = models.OneToOneField(
        'admin_dashboard.Shop',
        on_delete=models.CASCADE,
        related_name='wallet'
    )

    # Amount currently owed to the shop
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Total amount ever paid to this shop
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        verbose_name = "Shop Wallet"
        verbose_name_plural = "Shop Wallets"

        indexes = [
            models.Index(fields=['updated_at']),
        ]

    @property
    def available_balance(self):
        return self.pending_balance

    def __str__(self):

        return (
            f"{self.shop.name} | "
            f"Pending ₹{self.pending_balance}"
        )