from django.db import models
from django.utils.text import slugify

class CompanyInfo(models.Model):
    name = models.CharField(max_length=255, help_text="Company name")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True, null=True)
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For multi-company support, you could add:
    # company_code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name



class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)
    slug = models.SlugField(unique=True,blank=True,null=True)

    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug = slugify(self.name).lower()
        super().save(*args,**kwargs)

    def __str__(self):
        return self.name
    
    
from django.urls import reverse

from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    cost_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="What we pay the shopkeeper")
    size = models.CharField(max_length=50, default='N/A', help_text='e.g. 500 ml, 1 kg, 1 piece')
    
    # --- Inventory Cycle Fields ---
    stock_available = models.IntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5, help_text="Alert threshold for reordering")
    updated_at = models.DateTimeField(auto_now=True) # Tracks the last time stock was touched
    
    slug = models.SlugField(unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    # --- Logic Improvements ---
    @property
    def is_in_stock(self):
        """TEMPLATE USES THIS: Returns True if there is at least 1 item"""
        return self.stock_available > 0
    
    @property
    def discount_amount(self):
        """TEMPLATE USES THIS: For the 'SAVE ₹X' badge"""
        if self.discount_price:
            return int(self.price - self.discount_price)
        return 0

    def get_effective_price(self):
        """TEMPLATE USES THIS: To show the lower price if on sale"""
        return self.discount_price if self.discount_price else self.price
    
    @property
    def needs_restock(self):
        """Logic for the 'Reorder' badge in your template."""
        return self.stock_available <= self.min_stock_level

    @property
    def stock_status(self):
        """Returns a string for easier template styling."""
        if self.stock_available == 0:
            return "OUT_OF_STOCK"
        elif self.needs_restock:
            return "LOW_STOCK"
        return "IN_STOCK"

    @property
    def margin_per_unit(self):
        return self.get_effective_price() - self.cost_price
    
    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            self.slug = slugify(f"{self.name}-{self.id}")
            kwargs.pop('force_insert', None) 
        super().save(*args, **kwargs)

class ProductImage(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_images' )
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"{self.product.name} Image"


class StockLog(models.Model):
    TRANSACTION_TYPES = [
        ('RESTOCK', 'Stock Added'),
        ('SALE', 'Order Delivered'),
        ('WASTAGE', 'Damaged/Expired'),
        ('RETURN', 'Customer Returned'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='logs')
    change_amount = models.IntegerField() # e.g., +10 or -2
    reason = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True) # "Restocked for Village Festival"
#============================================================
class DeliveryHub(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Updated: More realistic default for village hyperlocal (e.g., 7km - 15km)
    max_delivery_radius_km = models.PositiveIntegerField(default=15)
    
    # NEW: Safety and Operational Fields
    is_active = models.BooleanField(default=True, db_index=True)
    is_accepting_orders = models.BooleanField(default=True)
    
    # NEW: Metadata for Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery Hub"
        verbose_name_plural = "Delivery Hubs"
        # Indexing coordinates makes distance calculations faster in the database
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    

class ShippingCost(models.Model):
    delivery_hub = models.ForeignKey(DeliveryHub, related_name='shipping_costs', on_delete=models.CASCADE)
    min_distance_km = models.FloatField()  # Minimum distance in km
    max_distance_km = models.FloatField()  # Maximum distance in km

    # Pricing
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Fee charged to the customer")
    rider_earning = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount the rider earns")
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Platform earnings from this delivery")

    class Meta:
        unique_together = ('delivery_hub', 'min_distance_km', 'max_distance_km')

    def __str__(self):
        return f"{self.delivery_hub.name} | {self.min_distance_km}-{self.max_distance_km} km | ₹{self.cost}"
#=========================================================================
