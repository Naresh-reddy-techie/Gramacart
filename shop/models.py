from django.db import models
from django.contrib.auth.models import User
from admin_dashboard.models import Product,DeliveryHub

class CustomerProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='customer_profile')
    phone_number = models.CharField(max_length=10)
   
    def __str__(self):
        return self.user.username


# =========================================================
# MODELS.py (PRODUCTION READY ADDRESS MODEL)
# =========================================================

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


# =========================================================
# ACTIVE ADDRESS MANAGER
# =========================================================

class ActiveAddressManager(models.Manager):

    def get_queryset(self):

        return super().get_queryset().filter(
            is_active=True
        )


# =========================================================
# ADDRESS
# =========================================================

class Address(models.Model):

    ADDRESS_TYPE = [
        ("home", "Home"),
        ("parents", "Parents"),
        ("work", "Work"),
        ("other", "Other"),
    ]

    # =====================================================
    # RELATIONS
    # =====================================================

    customer = models.ForeignKey(
        "CustomerProfile",
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    # =====================================================
    # USER DETAILS
    # =====================================================

    recipient_name = models.CharField(
        max_length=255
    )

    phone_number = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r"^[6-9]\d{9}$",
                message="Enter valid 10 digit mobile number."
            )
        ]
    )

    # =====================================================
    # ADDRESS DETAILS
    # =====================================================

    address_line = models.CharField(
        max_length=255
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100,
        default="Andhra Pradesh"
    )

    country = models.CharField(
        max_length=100,
        default="India"
    )

    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^\d{6}$",
                message="Enter valid 6 digit pincode."
            )
        ]
    )

    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE,
        default="home"
    )

    # =====================================================
    # GEO LOCATION
    # =====================================================

    latitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        db_index=True
    )

    longitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        db_index=True
    )

    # =====================================================
    # FUTURE SCALABILITY
    # =====================================================

    full_address = models.TextField(
        blank=True
    )

    is_remote = models.BooleanField(
        default=False
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_default = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # MANAGERS
    # =====================================================

    objects = models.Manager()

    active = ActiveAddressManager()

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = ["-is_default", "-created_at"]

        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["city"]),
            models.Index(fields=["pincode"]),
        ]

    # =====================================================
    # CLEAN
    # =====================================================

    def clean(self):

        if self.latitude is None or self.longitude is None:

            raise ValidationError(
                "Location coordinates missing."
            )

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        # ---------------------------------------------
        # NORMALIZATION
        # ---------------------------------------------

        self.recipient_name = (
            self.recipient_name.strip()
        )

        self.address_line = (
            self.address_line.strip()
        )

        self.city = (
            self.city.strip().title()
        )

        self.state = (
            self.state.strip().title()
        )

        self.country = (
            self.country.strip().title()
        )

        if self.landmark:
            self.landmark = (
                self.landmark.strip()
            )

        # ---------------------------------------------
        # FULL ADDRESS
        # ---------------------------------------------

        parts = [
            self.address_line,
            self.landmark,
            self.city,
            self.state,
            self.pincode,
            self.country
        ]

        self.full_address = ", ".join(
            [p for p in parts if p]
        )

        self.full_clean()

        super().save(*args, **kwargs)

    # =====================================================
    # SOFT DELETE
    # =====================================================

    def deactivate(self):

        self.is_active = False

        self.save(update_fields=["is_active"])

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.recipient_name} - "
            f"{self.city}"
        )
#===============================================

from admin_dashboard.models import ProductVariant
from inventory.models import Inventory 
#==================================
class CartItem(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    hub = models.ForeignKey(
        DeliveryHub,
        on_delete=models.PROTECT,
        db_index=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE
    )

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'variant', 'hub'],
                name='unique_cart_per_hub_variant'
            )
        ]
        ordering = ['-added_on']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.variant.display_name} x {self.quantity}"
#====================================================================

class WishlistItem(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together =('user','product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

#===========================================================
import random
import uuid
from django.db import models
from django.contrib.auth.models import User
from admin_dashboard.models import Shop,DeliveryHub
from decimal import Decimal

def generate_order_number():
    # Returns ORD-A1B2C3D4
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Order Placed'),        # Customer just placed it
        ('declined', 'Declined'),      # Admin rejected (e.g., out of stock)
        ('packed', 'Packed'),          # Shop ready! Admin can now assign rider
        ('assigned', 'Rider Assigned'),#rider travelling to hub
        ('out_for_delivery', 'Out for Delivery'), # Rider started delivery
        ('delivered', 'Delivered'),    # Final success
        ('cancelled', 'Cancelled'),    # Customer/Admin cancelled
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number, editable=False)
    address = models.ForeignKey('Address', on_delete=models.PROTECT)
    shop = models.ForeignKey(Shop,on_delete=models.SET_NULL,null=True,blank=True,related_name='orders')
    hub = models.ForeignKey(DeliveryHub,on_delete=models.SET_NULL,null=True,blank=True,related_name='orders',db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',db_index=True)

    # REJECTION LOGIC
    # This allows the admin to explain WHY a village delivery failed
    rejection_reason = models.TextField(null=True, blank=True, help_text="Reason shown to customer if order is cancelled")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False) # Total is calculated, not edited

    notes = models.TextField(blank=True, null=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True,blank=True)
    
    # Live Tracking for Village Riders
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    #New Token Field
    delivery_token = models.CharField(max_length=4,blank=True,null=True,help_text="4-digit PIN for delivery verification")
    is_ledger_created = models.BooleanField(default=False)
    #calculating for estimate delivery
    estimated_distance_km = models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    estimated_eta_minutes = models.PositiveIntegerField(null=True,blank=True)
    
    def save(self, *args, **kwargs):

        if not self.hub:
            raise ValueError("Order must have a hub assigned")

        if self.shop and self.hub:
            if self.shop.hub_id != self.hub_id:
                raise ValueError("Selected shop does not belong to the selected hub")

        #Generate token if it doesn't exist
        if not self.delivery_token:
            self.delivery_token=str(random.randint(1000,9999))
        # Automatically calculate total before saving to DB

        self.total = (self.subtotal + self.tax + self.shipping_cost + Decimal("0.00"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} - {self.user.username}"

    @property
    def is_paid(self):
        return self.payments.filter(status='success').exists()

    @property
    def display_status(self):
        mapping = {
            'pending': 'Order Placed',
            'packed': 'Packed & Ready',
            'assigned': 'Rider Assigned',
            'out_for_delivery': 'Out For Delivery',
            'delivered': 'Delivered',
            'declined': 'Cancelled',
            'cancelled': 'Cancelled',
        }
        return mapping.get(self.status, 'Order Placed')
    
    @property
    def progress(self):

        mapping = {

            'pending': 20,

            'packed': 55,

            'assigned': 55,

            'out_for_delivery': 85,

            'delivered': 100,

            'declined': 0,

            'cancelled': 0,
        }

        return mapping.get(self.status, 0)
    
    
    @property
    def payment(self):

        return (
            self.payments
            .select_related("method")
            .order_by("-created_at")
            .first()
        )
    
    @property
    def payment_status_display(self):

        payment = self.payment

        if not payment:
            return "Unavailable"

        if payment.status == "success":
            return "Paid"

        if payment.status == "failed":
            return "Failed"

        if payment.status == "refunded":
            return "Refunded"

        if payment.method.name.lower() == "cod":
            return "Cash On Delivery"

        return "Pending"
    
    @property
    def payment_method_display(self):

        payment = self.payment

        if not payment:
            return "-"

        return payment.method.display_name
    

    @property
    def can_track(self):

     
        return self.status in [

            "assigned",
            "out_for_delivery"

        ]
    

    @property
    def show_otp(self):

  
        return self.status in [

            "assigned",
            "out_for_delivery"

        ] and bool(self.delivery_token)
 

    @property
    def estimated_delivery_text(self):

        
        mapping = {

            "pending": "Order Confirmation Pending",

            "confirmed": "Preparing Your Order",

            "packed": "Ready For Dispatch",

            "assigned": "Rider Assigned",

            "out_for_delivery": "Arriving Soon",

            "delivered": "Delivered Successfully",

            "cancelled": "Order Cancelled",

            "declined": "Order Declined",

        }

        return mapping.get(
            self.status,
            "Processing"
        )
 

from inventory.models import Inventory

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=True
    )

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )

    quantity = models.PositiveIntegerField()

    # snapshot price
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # snapshot variant name
    variant_name = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-id']

    @property
    def get_total(self):
        return self.quantity * self.price
    

    def __str__(self):

        if self.variant_name:
            return (
                f"{self.product.name} - "
                f"{self.variant_name} x {self.quantity}"
            )

        return (
            f"{self.product.name} x {self.quantity}"
        )

class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # 🔥 IMPORTANT: link rating to order
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)

    score = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user', 'order')  # stronger protection