from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

from shop.models import Order
from admin_dashboard.models import DeliveryHub

# ------------------- Constants -------------------

class DeliveryStatus(models.TextChoices):
    """Using TextChoices for better Django integration and readability."""

    PENDING = 'pending', 'Order Placed'
    PACKED = 'packed', 'Packed'
    ASSIGNED = 'assigned', 'Assigned'
    OUT = 'out_for_delivery', 'Out for Delivery'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'
# ------------------- Delivery Profile -------------------

class DeliveryProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_profile')
    hub = models.ForeignKey(DeliveryHub, on_delete=models.SET_NULL, null=True, blank=True, related_name='riders')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    is_online = models.BooleanField(default=False,db_index=True)
    last_duty_toggle = models.DateTimeField(null=True,blank=True)

    VEHICLE_CHOICES = [('bike', 'Bike'), ('cycle', 'Cycle'), ('auto', 'Auto/Van')]
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default='bike')

    @property
    def status_label(self):
        return "Online" if self.is_online else "Offline"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.hub.name if self.hub else 'Floating'}"

# ------------------- Delivery Model -------------------

class Delivery(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    delivery_boy = models.ForeignKey(
        User,
        limit_choices_to=Q(groups__name='DeliveryBoy'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_deliveries'
    )
    status = models.CharField(
        max_length=20, 
        choices=DeliveryStatus.choices, 
        default=DeliveryStatus.PENDING,
        db_index=True
    )

    # Logistics & Geography
    nearest_hub = models.ForeignKey(DeliveryHub, null=True, blank=True, on_delete=models.SET_NULL)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Proof & Experience
    proof_photo = models.ImageField(upload_to='delivery_proofs/%Y/%m/', null=True, blank=True)
    tracking_notes = models.TextField(null=True, blank=True, help_text="Rider notes about village drop-off.")

    # Frozen Financials (Crucial for Startup Auditing)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    rider_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    # Live Tracking (Decimal is better for precision than Float)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(auto_now=True)
    
    # Settlement (For COD operations)
    cod_collected = models.BooleanField(default=False)  
    cod_submitted = models.BooleanField(default=False)  
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Deliveries"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'delivery_boy']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Delivery {self.id} | {self.status_display}"

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def status_color(self):
        colors = {
            DeliveryStatus.PENDING: 'warning',
            DeliveryStatus.ASSIGNED: 'primary',
            DeliveryStatus.OUT: 'info',
            DeliveryStatus.DELIVERED: 'success',
            DeliveryStatus.CANCELLED: 'danger',
        }
        return colors.get(self.status, 'secondary')

    def save(self, *args, **kwargs):
        # Handle timestamp automation on status change
        if self.pk:
            old_status = Delivery.objects.get(pk=self.pk).status
            if old_status != self.status:
                if self.status == DeliveryStatus.DELIVERED:
                    self.delivered_at = timezone.now()
                elif self.status == DeliveryStatus.OUT:
                    self.out_for_delivery_at = timezone.now()
                elif self.status == DeliveryStatus.ASSIGNED:
                    self.assigned_at = timezone.now()

        super().save(*args, **kwargs)

