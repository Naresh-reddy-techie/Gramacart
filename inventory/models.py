from django.db import models, transaction
from django.db.models import Q, F
from django.core.exceptions import ValidationError


# ============================================================
# INVENTORY
# ============================================================

class Inventory(models.Model):

    variant = models.ForeignKey(
        'admin_dashboard.ProductVariant',
        on_delete=models.CASCADE,
        related_name='inventory_items',
        db_index=True
    )

    shop = models.ForeignKey(
        'admin_dashboard.Shop',
        on_delete=models.CASCADE,
        related_name='inventory',
        db_index=True
    )

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    stock = models.PositiveIntegerField(default=0)

    min_stock_level = models.PositiveIntegerField(default=5)

    max_order_quantity = models.PositiveIntegerField(default=10)

    # --------------------------------------------------------
    # PRICING
    # --------------------------------------------------------

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    updated_at = models.DateTimeField(auto_now=True)

    # --------------------------------------------------------
    # META
    # --------------------------------------------------------

    class Meta:

        unique_together = ('variant', 'shop')

        ordering = ['-updated_at']

        indexes = [
            models.Index(fields=['shop']),
            models.Index(fields=['variant']),
            models.Index(fields=['shop', 'variant']),
        ]

        constraints = [

            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='inventory_stock_non_negative'
            ),

            models.CheckConstraint(
                condition=Q(
                    selling_price__gte=F('cost_price')
                ),
                name='inventory_selling_gte_cost'
            ),
        ]

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):

        if self.cost_price < 0:
            raise ValidationError(
                "Cost price cannot be negative."
            )

        if self.selling_price < 0:
            raise ValidationError(
                "Selling price cannot be negative."
            )

        if self.selling_price < self.cost_price:
            raise ValidationError(
                "Selling price cannot be lower than cost price."
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    # ========================================================
    # STOCK INCREASE
    # ========================================================

    def increase_stock(
        self,
        qty,
        reason="RESTOCK",
        note=""
    ):

        if qty <= 0:
            raise ValidationError(
                "Quantity must be greater than zero."
            )

        with transaction.atomic():

            inventory = Inventory.objects.select_for_update().get(
                pk=self.pk
            )

            inventory.stock += qty

            inventory.save(
                update_fields=['stock', 'updated_at']
            )

            StockLog.objects.create(
                inventory=inventory,
                change_amount=qty,
                reason=reason,
                note=note
            )

            return inventory

    # ========================================================
    # STOCK REDUCTION
    # ========================================================

    def reduce_stock(
        self,
        qty,
        reason="SALE",
        note=""
    ):

        if qty <= 0:
            raise ValidationError(
                "Quantity must be greater than zero."
            )

        with transaction.atomic():

            inventory = Inventory.objects.select_for_update().get(
                pk=self.pk
            )

            if inventory.stock < qty:

                raise ValidationError(
                    f"Only {inventory.stock} items available."
                )

            inventory.stock -= qty

            inventory.save(
                update_fields=['stock', 'updated_at']
            )

            StockLog.objects.create(
                inventory=inventory,
                change_amount=-qty,
                reason=reason,
                note=note
            )

            return inventory

    # ========================================================
    # HELPERS
    # ========================================================

    @property
    def is_low_stock(self):

        return self.stock <= self.min_stock_level

    @property
    def available_for_order(self):

        return min(
            self.stock,
            self.max_order_quantity
        )

    @property
    def stock_status(self):

        if self.stock <= 0:
            return "OUT_OF_STOCK"

        if self.is_low_stock:
            return "LOW_STOCK"

        return "IN_STOCK"

    # ========================================================
    # STRING
    # ========================================================

    def __str__(self):

        return f"{self.variant} @ {self.shop.name}"


# ============================================================
# STOCK LOG
# ============================================================

class StockLog(models.Model):

    TRANSACTION_TYPES = [

        ('RESTOCK', 'Stock Added'),

        ('SALE', 'Customer Order'),

        ('RETURN', 'Reusable Return'),

        ('DAMAGED_RETURN', 'Damaged Return'),

        ('WASTAGE', 'Broken/Damaged'),

        ('EXPIRED', 'Expired Product'),

        ('TRANSFER_IN', 'Transfer In'),

        ('TRANSFER_OUT', 'Transfer Out'),
    ]

    inventory = models.ForeignKey(
        'inventory.Inventory',
        on_delete=models.CASCADE,
        related_name='logs'
    )

    # +10 / -2 etc
    change_amount = models.IntegerField()

    reason = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        db_index=True
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:

        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['reason']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):

        return (
            f"{self.inventory.variant} | "
            f"{self.change_amount}"
        )