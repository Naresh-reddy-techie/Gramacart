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


from django.utils import timezone

from django.core.exceptions import ValidationError


def validate_banner_image(image):
    if image.size > 2 * 1024 * 1024:
        raise ValidationError('Image must be under 2MB.')

class Banner(models.Model):

    PAGE_CHOICES = [
        ('home',     'Homepage'),
        ('shop',     'Shop / Dashboard'),
        ('category', 'Category Page'),
        ('all',      'All Pages'),
    ]

    TYPE_CHOICES = [
        ('promo',        'Promo / Offer'),
        ('announcement', 'Announcement'),
        ('seasonal',     'Seasonal Greeting'),
        ('app',          'App Download Nudge'),
    ]

    hub = models.ForeignKey(
        'DeliveryHub',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='banners',
        help_text='Leave blank for a global banner shown to all hubs'
    )

    # Content
    title       = models.CharField(max_length=120)
    subtitle    = models.CharField(max_length=200, blank=True)
    eyebrow     = models.CharField(max_length=60,  blank=True)
    offer_label = models.CharField(max_length=30,  blank=True)
    image       = models.ImageField(
        upload_to='banners/',
        blank=True,
        null=True,
        validators=[validate_banner_image],
        help_text='Recommended: 800×300px, under 2MB'
    )

    # CTA
    cta_text = models.CharField(max_length=40,  blank=True, default='Shop now')
    cta_url  = models.CharField(max_length=200, blank=True, default='/shop/')

    # Classification
    page        = models.CharField(max_length=20, choices=PAGE_CHOICES, default='shop')
    banner_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='promo')

    # Scheduling
    start_date = models.DateTimeField(null=True, blank=True)
    end_date   = models.DateTimeField(null=True, blank=True)

    # Control
    is_active = models.BooleanField(default=True)
    order     = models.PositiveIntegerField(default=0)

    # Analytics — editable=False keeps them out of the form
    click_count      = models.PositiveIntegerField(default=0, editable=False)
    impression_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['order', '-start_date']

    def __str__(self):
        hub_name = self.hub.name if self.hub else 'Global'
        return f"{self.title} — {hub_name}"

    def is_live(self):
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active

class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)
    image = models.ImageField(upload_to='categories/',blank=True,null=True)
    slug = models.SlugField(unique=True,blank=True,null=True)

    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug = slugify(self.name).lower()
        super().save(*args,**kwargs)

    def __str__(self):
        return self.name

from django.db import models
from django.utils.text import slugify
from django.db.models import Avg
from django.db.models import Min

class Product(models.Model):

    

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    category = models.ForeignKey('Category', on_delete=models.CASCADE)


    slug = models.SlugField(unique=True, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    # ⭐ Ratings
    @property
    def avg_rating(self):
        return self.ratings.aggregate(avg=Avg('score'))['avg'] or 0

    @property
    def rating_count(self):
        return self.ratings.count()

    

    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            self.slug = slugify(f"{self.name}-{self.id}")
            Product.objects.filter(id=self.id).update(slug=self.slug)
            return
        super().save(*args, **kwargs)

class ProductVariant(models.Model):
    product = models.ForeignKey(
        'admin_dashboard.Product',
        on_delete=models.CASCADE,
        related_name='variants'
    )

    UNIT_CHOICES = [
        ('ml', 'Millilitre'),
        ('ltr', 'Litre'),
        ('g', 'Gram'),
        ('kg', 'Kilogram'),
        ('pcs', 'Pieces'),
        ('pack', 'Pack'),
    ]

    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    # auto-generated display (NO manual mistakes)
    @property
    def display_name(self):
        return f"{self.quantity}{self.unit}"

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'unit', 'quantity')

    def __str__(self):
        return f"{self.product.name} - {self.quantity}{self.unit}"


class ProductImage(models.Model):
    product = models.ForeignKey( Product, on_delete=models.CASCADE, related_name='product_images' ) 
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
from django.contrib.auth.models import User


class DeliveryHub(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User,on_delete=models.CASCADE,related_name="owned_hubs",null=True,blank=True)
    state = models.CharField(max_length=100,default="Andhra Pradesh",db_index=True)
    district = models.CharField(max_length=100,db_index=True)
    mandal = models.CharField(max_length=100,db_index=True)
    village = models.CharField(max_length=100,db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Updated: More realistic default for village hyperlocal (e.g., 7km - 15km)
    max_delivery_radius_km = models.PositiveIntegerField(default=15)
    # ADDRESS (FIXED)
    full_address = models.TextField(blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)

    # NEW: Safety and Operational Fields
    is_active = models.BooleanField(default=True, db_index=True)
    is_accepting_orders = models.BooleanField(default=True)
    
    # NEW: Metadata for Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = "Delivery Hub"

        verbose_name_plural = "Delivery Hubs"

        indexes = [

            models.Index(fields=['latitude', 'longitude']),

            models.Index(fields=['state', 'district']),

            models.Index(fields=['district', 'mandal']),

            models.Index(fields=['village']),
        ]
        ordering = [
            'state',
            'district',
            'mandal',
            'village'
        ]

        unique_together = (
            'name',
            'state',
            'district',
            'mandal',
            'village'
        )

    def __str__(self):
        return (
            f"{self.name} | "
            f"{self.village}, "
            f"{self.mandal}"
        )

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

from django.db import models

class SellerApplication(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    BUSINESS_TYPES = [
        ('HOME_MADE', 'Home Made Products'),
        ('CRAFTS', 'Handicrafts'),
        ('FOOD', 'Food Business'),
        ('KIRANA', 'Retail Shop'),
        ('OTHER', 'Other'),
    ]

    owner_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=15)

    email = models.EmailField(blank=True, null=True)

    village = models.CharField(max_length=150)

    business_name = models.CharField(max_length=150)

    business_type = models.CharField(
        max_length=30,
        choices=BUSINESS_TYPES
    )

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    hub = models.ForeignKey('DeliveryHub',on_delete=models.SET_NULL,null=True,blank=True,related_name='seller_applications')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} ({self.status})"




#Base of everything (ledger,dispatch,profit)

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

class Shop(models.Model):

    SHOP_TYPES = [
        ('KIRANA', 'Kirana Store'),
        ('DARK_STORE', 'Dark Store'),
        ('WAREHOUSE', 'Warehouse'),
    ]

    seller_application = models.OneToOneField(
        'SellerApplication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shop'
    )

    name = models.CharField(
        max_length=150
    )

    shop_type = models.CharField(
        max_length=25,
        choices=SHOP_TYPES,
        db_index=True
    )

    hub = models.ForeignKey(
        'DeliveryHub',
        on_delete=models.CASCADE,
        related_name='shops',
        db_index=True
    )

    # Marketplace commission percentage.
    # Used only for external shops.
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Marketplace commission percentage for this shop."
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    is_internal = models.BooleanField(
        default=False,
        help_text="True if owned by GramaCart (Dark Store/Warehouse)."
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['name']

        unique_together = (
            'name',
            'hub'
        )

        indexes = [
            models.Index(fields=['hub', 'shop_type']),
            models.Index(fields=['hub', 'is_active']),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(commission_percent__gte=0),
                name='shop_commission_gte_zero'
            ),
            models.CheckConstraint(
                condition=Q(commission_percent__lte=100),
                name='shop_commission_lte_hundred'
            ),
        ]

    def clean(self):

        super().clean()

        if self.commission_percent < 0:
            raise ValidationError(
                "Commission cannot be negative."
            )

        if self.commission_percent > 100:
            raise ValidationError(
                "Commission cannot exceed 100%."
            )

        # Internal GramaCart shops do not require commission.
        if self.is_internal:
            self.commission_percent = 0

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    # =====================================================
    # BUSINESS HELPERS
    # =====================================================

    @property
    def requires_payout(self):

        return not self.is_internal

    @property
    def can_fulfill_orders(self):

        return self.shop_type in (
            'KIRANA',
            'DARK_STORE'
        )

    @property
    def is_dark_store(self):

        return self.shop_type == 'DARK_STORE'

    @property
    def is_warehouse(self):

        return self.shop_type == 'WAREHOUSE'

    @property
    def is_kirana(self):

        return self.shop_type == 'KIRANA'

    def __str__(self):

        return (
            f"{self.name} "
            f"({self.get_shop_type_display()})"
        )
#==============================================================
# Order → Delivered → Ledger → Money tracked [for warehouse]
# Internal → No payout → Only profit tracking[for darkstore]
#You BUY from them → You PAY them → Ledger needed [for kirana stores]✅

from django.core.exceptions import ValidationError

class ShopLedger(models.Model):
    shop = models.ForeignKey('admin_dashboard.Shop', on_delete=models.CASCADE, related_name='ledger_entries')
    hub = models.ForeignKey('admin_dashboard.DeliveryHub', on_delete=models.CASCADE, related_name='ledger_entries')
    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.CASCADE,
        related_name='ledger_entries'
    )

    inventory = models.ForeignKey(
        'inventory.Inventory',
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_settled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order','inventory', 'shop')
        indexes = [
            models.Index(fields=['shop', 'created_at']),
            models.Index(fields=['hub', 'created_at']),
        ]

    def clean(self):
        super().clean()

        if not self.inventory:
            raise ValidationError("Inventory is required")

        if not self.order:
            raise ValidationError("Order is required")

        if self.inventory.shop != self.shop:
            raise ValidationError("Inventory does not belong to this shop")

        if self.cost_price < 0 or self.selling_price < 0:
            raise ValidationError("Prices cannot be negative")

        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")
            
    def save(self, *args, **kwargs):
        self.full_clean()

        if self.inventory:   # ✅ SAFE CHECK
            self.cost_price = self.inventory.cost_price
            self.selling_price = self.inventory.selling_price

            self.total_cost = self.cost_price * self.quantity
            self.total_revenue = self.selling_price * self.quantity
            self.profit = self.total_revenue - self.total_cost

        super().save(*args, **kwargs)

    def __str__(self):
       
        order_num = self.order.order_number if self.order else "NoOrder"
        return f"{self.shop.name} - {order_num}"
    

#==================================================

from django.contrib.auth.models import User
#it only support one hub one partner. 

class HubPartnerProfile(models.Model):

    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name = "hub_partner_profile")
    hub = models.OneToOneField(DeliveryHub,on_delete=models.PROTECT,related_name="partner")
    phone = models.CharField(max_length=15,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.hub.name}"
    

from django.utils import timezone


class HubSubscription(models.Model):

    PLAN_CHOICES = [
        
        ("YEARLY", "Yearly"),
    ]

    partner = models.OneToOneField(HubPartnerProfile,on_delete=models.CASCADE,related_name="subscription")
    plan = models.CharField(max_length=20,choices=PLAN_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    renewal_reminder_sent = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100,blank=True)

    @property
    def is_expired(self):
        return timezone.now().date() > self.end_date

    def __str__(self):
        return f"{self.partner.hub.name} - {self.plan}"
    

#==============================================================