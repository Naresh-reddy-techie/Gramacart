from django.db import models
from django.contrib.auth.models import User
from admin_dashboard.models import Product

class CustomerProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='customer_profile')
    phone_number = models.CharField(max_length=10)
   
    def __str__(self):
        return self.user.username



class Address(models.Model):

    ADDRESS_TYPE = [
        ('home', 'Home'),
        ('parents', 'Parents'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(
        'CustomerProfile',
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    recipient_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    address_line = models.CharField(max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=6, blank=True, null=True)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE, default='home')

    latitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Soft delete toggle")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['latitude', 'longitude'])]

    def __str__(self):
        return f"{self.recipient_name} - {self.city}"

    # Logic to handle deletion safely
    def deactivate(self):
        self.is_active = False
        self.save()


class CartItem(models.Model):
    user = models.ForeignKey(User,on_delete = models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_on = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.user.username}-{self.product.name}x{self.quantity}"

#====================================================================

class WishlistItem(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

#===========================================================
import random
import uuid
from django.db import models
from django.contrib.auth.models import User

def generate_order_number():
    # Returns ORD-A1B2C3D4
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Order Placed'),        # Customer just placed it
        ('confirmed', 'Confirmed'),    # Admin/Shop accepted it
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

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
    
    # Live Tracking for Village Riders
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    #New Token Field
    delivery_token = models.CharField(max_length=4,blank=True,null=True,help_text="4-digit PIN for delivery verification")

    def save(self, *args, **kwargs):
        #Generate token if it doesn't exist
        if not self.delivery_token:
            self.delivery_token=str(random.randint(1000,9999))
        # Automatically calculate total before saving to DB
        self.total = self.subtotal + self.tax + self.shipping_cost
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
            'confirmed': 'Order Placed',
            'packed': 'Packed',
            'assigned': 'In Transit',
            'out_for_delivery': 'In Transit',
            'delivered': 'Delivered',
            'declined': 'Cancelled',
            'cancelled': 'Cancelled',
        }
        return mapping.get(self.status, 'Order Placed')
    
    @property
    def progress(self):
        mapping = {
            'pending': 10,
            'confirmed': 10,
            'packed': 50,
            'assigned': 50,
            'out_for_delivery': 75,
            'delivered': 100,
            'declined': 0,
            'cancelled': 0,
        }
        return mapping.get(self.status, 0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at the time of order

    def get_total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


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