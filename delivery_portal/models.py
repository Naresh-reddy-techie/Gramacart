
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

from shop.models import Order
from admin_dashboard.models import DeliveryHub


# =========================================================
# DELIVERY STATUS
# =========================================================

class DeliveryStatus(models.TextChoices):

    PENDING = "pending", "Pending"

    PACKED = "packed", "Packed"

    ASSIGNED = "assigned", "Assigned"

    OUT_FOR_DELIVERY = "out_for_delivery", "Out For Delivery"

    DELIVERED = "delivered", "Delivered"

    CANCELLED = "cancelled", "Cancelled"

    FAILED = "failed", "Failed Delivery"


# =========================================================
# DELIVERY PROFILE
# =========================================================

class DeliveryProfile(models.Model):

    VEHICLE_CHOICES = [
        ("bike", "Bike"),
        ("cycle", "Cycle"),
        ("auto", "Auto"),
        ("van", "Van"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="delivery_profile"
    )

    hub = models.ForeignKey(
        DeliveryHub,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="riders"
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    vehicle_type = models.CharField(
        max_length=10,
        choices=VEHICLE_CHOICES,
        default="bike"
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    is_online = models.BooleanField(
        default=False,
        db_index=True
    )

    last_duty_toggle = models.DateTimeField(
        null=True,
        blank=True
    )

    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    last_location_update = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):

        return (
            f"{self.user.username} - "
            f"{self.hub.name if self.hub else 'No Hub'}"
        )


# =========================================================
# DELIVERY
# =========================================================

class Delivery(models.Model):

    # =====================================================
    # CORE
    # =====================================================

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery"
    )

    delivery_boy = models.ForeignKey(
        User,
        limit_choices_to=Q(groups__name="DeliveryBoy"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_deliveries"
    )

    nearest_hub = models.ForeignKey(
        DeliveryHub,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries"
    )

    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True
    )

    # =====================================================
    # DISTANCE
    # =====================================================

    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =====================================================
    # FINANCIALS
    # =====================================================

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    rider_earning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =====================================================
    # COD SETTLEMENT
    # =====================================================

    cod_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    cod_collected = models.BooleanField(
        default=False,
        db_index=True
    )

    cod_submitted = models.BooleanField(
        default=False,
        db_index=True
    )

    cod_collected_at = models.DateTimeField(
        null=True,
        blank=True
    )

    cod_submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =====================================================
    # DELIVERY OTP
    # =====================================================

    otp_verified = models.BooleanField(
        default=False
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =====================================================
    # LIVE TRACKING
    # =====================================================

    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    last_location_update = models.DateTimeField(
        null=True,
        blank=True
    )

    # =====================================================
    # PROOF
    # =====================================================

    proof_photo = models.ImageField(
        upload_to="delivery_proofs/%Y/%m/",
        null=True,
        blank=True
    )

    tracking_notes = models.TextField(
        blank=True,
        null=True
    )

    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    assigned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    picked_from_hub_at = models.DateTimeField(
        null=True,
        blank=True
    )

    out_for_delivery_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = ["-created_at"]

        indexes = [

            models.Index(fields=["status"]),

            models.Index(fields=["delivery_boy"]),

            models.Index(fields=["nearest_hub"]),

            models.Index(fields=["cod_collected"]),

            models.Index(fields=["cod_submitted"]),

            models.Index(fields=["created_at"]),
        ]

    # =====================================================
    # SAVE LOGIC
    # =====================================================

    def save(self, *args, **kwargs):

        if self.pk:

            old = Delivery.objects.get(pk=self.pk)

            if old.status != self.status:

                now = timezone.now()

                if self.status == DeliveryStatus.ASSIGNED:
                    self.assigned_at = now

                elif self.status == DeliveryStatus.OUT_FOR_DELIVERY:
                    self.out_for_delivery_at = now

                elif self.status == DeliveryStatus.DELIVERED:
                    self.delivered_at = now

                elif self.status == DeliveryStatus.CANCELLED:
                    self.cancelled_at = now

        super().save(*args, **kwargs)

    # =====================================================
    # HELPERS
    # =====================================================

    @property
    def is_cod(self):

        payment = self.order.payment

        if not payment:
            return False

        return payment.method.name.lower() == "cod"

    @property
    def customer_paid(self):

        if self.is_cod:
            return self.cod_collected

        payment = self.order.payment

        return (
            payment and
            payment.status == "success"
        )

    @property
    def rider_can_complete(self):

        if self.is_cod:
            return self.cod_collected and self.otp_verified

        return self.otp_verified

    def __str__(self):

        return (
            f"{self.order.order_number} - "
            f"{self.get_status_display()}"
        )

