from django import forms
from .models import Category,CompanyInfo

class CompanyInfoForm(forms.ModelForm):
    class Meta:
        model = CompanyInfo
        fields = [
            'name',
            'logo',
            'tagline',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'country',
            'pincode',
            'phone',
            'email',
            'website',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tagline / Slogan'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode / ZIP'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Website URL'}),
        }

        def __init__(self, *args, **kwargs):
            super(CompanyInfoForm, self).__init__(*args, **kwargs)
            # You can add custom validation or initial logic if needed
            # Example: If there is an existing logo, show it in the form
            if self.instance and self.instance.logo:
                self.fields['logo'].initial = self.instance.logo


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields=['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
        }



from django.forms import inlineformset_factory

from .models import (
    Product,
    ProductVariant,
    ProductImage,
    Category,
    StockLog,
)

# =========================================================
# PRODUCT FORM
# =========================================================

class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            'name',
            'description',
            'category',
            'is_active'
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product Name'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the product clearly...'
            }),

            'category': forms.Select(attrs={
                'class': 'form-select'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# =========================================================
# PRODUCT VARIANT FORM
# =========================================================

class ProductVariantForm(forms.ModelForm):

    class Meta:
        model = ProductVariant

        fields = [
            'unit',
            'quantity',
            'is_active'
        ]

        widgets = {

            'unit': forms.Select(attrs={
                'class': 'form-select'
            }),

            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 250 / 500 / 1',
                'step': '0.01',
                'min': '0'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_quantity(self):

        quantity = self.cleaned_data.get('quantity')

        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero"
            )

        return quantity


# =========================================================
# PRODUCT IMAGE FORMSET
# =========================================================



ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=['image'],
    extra=5,
    max_num=5,
    validate_max=True,
    can_delete=True
)

# =========================================================
# PRODUCT VARIANT FORMSET
# =========================================================

ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    extra=3,
    max_num=3,
    validate_max=True,
    can_delete=True
)

class StockLogForm(forms.ModelForm):
    class Meta:
        model = StockLog
        fields = ['change_amount', 'reason', 'note']
        widgets = {
            'change_amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Amount (use negative for wastage)'
            }),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Reason for change (e.g., Damaged during transit)'
            }),
        }

    def clean_change_amount(self):
        amount = self.cleaned_data.get('change_amount')
        if amount == 0:
            raise forms.ValidationError("Change amount cannot be zero.")
        return amount
    
from .models import ProductImage

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }



#==========================================================




from .models import DeliveryHub


class DeliveryHubForm(forms.ModelForm):

    class Meta:

        model = DeliveryHub

        fields = [

            'name',

            'state',
            'district',
            'mandal',
            'village',

            'latitude',
            'longitude',

            'full_address',
            'landmark',

            'max_delivery_radius_km',

            'is_active',
            'is_accepting_orders',
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: GramaCart Kaza'
            }),

            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),

            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'District'
            }),

            'mandal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mandal'
            }),

            'village': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Village'
            }),

            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any'
            }),

            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any'
            }),

            'full_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full pickup location for riders'
            }),

            'landmark': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nearby landmark'
            }),

            'max_delivery_radius_km': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'is_accepting_orders': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

from .models import ShippingCost
from admin_dashboard.models import DeliveryHub

class ShippingCostForm(forms.ModelForm):

    class Meta:
        model = ShippingCost
        fields = [
            'delivery_hub',
            'min_distance_km',
            'max_distance_km',
            'cost',
            'rider_earning',
            'platform_fee',
        ]

        widgets = {
            'delivery_hub': forms.Select(attrs={'class': 'form-control'}),
            'min_distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'rider_earning': forms.NumberInput(attrs={'class': 'form-control'}),
            'platform_fee': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
from payments.models import PaymentMethod
from django.conf import settings

class PaymentMethodForm(forms.ModelForm):
    # Use the registry to define choices
    PAYMENT_METHOD_CHOICES = [
        (k, k.replace('_', ' ').title()) 
        for k in settings.PAYMENT_GATEWAY_CONFIG_FIELDS.keys()
    ]
    
    name = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'modern-input'})
    )

    class Meta:
        model = PaymentMethod
        fields = ['name', 'display_name', 'is_active', 'sort_order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Collect every possible config key across all gateways
        all_config_fields = set()
        for fields in settings.PAYMENT_GATEWAY_CONFIG_FIELDS.values():
            all_config_fields.update(fields)

        # 2. Add them to the form dynamically
        for field_name in sorted(all_config_fields):
            # Professional Touch: Prettier labels for technical keys
            pretty_label = field_name.replace('_', ' ').upper()
            
            self.fields[field_name] = forms.CharField(
                required=False,
                label=pretty_label,
                widget=forms.TextInput(attrs={
                    'placeholder': f'Enter {pretty_label}...',
                    'class': 'modern-input'
                })
            )

        # 3. Pre-fill initial values from the JSON field
        if self.instance and self.instance.config:
            for key, value in self.instance.config.items():
                if key in self.fields:
                    self.fields[key].initial = value

    def clean(self):
        cleaned_data = super().clean()
        method_name = cleaned_data.get("name")
        
        # Identify which fields are ACTUALLY required for the selected gateway
        required_fields = settings.PAYMENT_GATEWAY_CONFIG_FIELDS.get(method_name, [])
        
        config_data = {}
        for field in required_fields:
            val = cleaned_data.get(field)
            if not val:
                # Validation: Don't allow empty keys for active gateways
                self.add_error(field, f"This field is required for {method_name.upper()}.")
            config_data[field] = val

        # Security: Overwrite the config to ONLY include allowed fields
        # This prevents "Ghost Data" from old configurations staying in the DB
        cleaned_data['config'] = config_data
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Directly inject the cleaned config into the model instance
        instance.config = self.cleaned_data.get('config', {})
        if commit:
            instance.save()
        return instance
    


from django import forms
from .models import Shop


class ShopForm(forms.ModelForm):

    class Meta:
        model = Shop

        fields = [
            'name',
            'shop_type',
            'hub',
            'phone',
            'address',
            'is_internal',
            'is_active'
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter shop name'
            }),

            'shop_type': forms.Select(attrs={
                'class': 'form-select'
            }),

            'hub': forms.Select(attrs={
                'class': 'form-select'
            }),

            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),

            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter address'
            }),

            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_name(self):

        name = self.cleaned_data['name'].strip()

        if len(name) < 2:
            raise forms.ValidationError("Shop name is too short")

        return name


#====================================================

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import (
    HubPartnerProfile,
    HubSubscription,
    DeliveryHub
)

# =========================================================
# HUB PARTNER FORM
# =========================================================

class HubPartnerForm(forms.ModelForm):

    class Meta:
        model = HubPartnerProfile
        fields = ["hub", "phone", "is_active"]

        widgets = {
            "hub": forms.Select(attrs={"class": "form-select"}),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Partner Mobile Number"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NEW: safe hub filtering (create + edit safe)
        if self.instance.pk:
            self.fields["hub"].queryset = DeliveryHub.objects.filter(is_active=True)
        else:
            self.fields["hub"].queryset = DeliveryHub.objects.filter(
                partner__isnull=True,
                is_active=True
            ).order_by("name")


# =========================================================
# SUBSCRIPTION FORM
# =========================================================
class HubSubscriptionForm(forms.ModelForm):

    class Meta:
        model = HubSubscription

        fields = [
            "plan",
            "start_date",
            "amount",
            "payment_reference",
            "is_active",
        ]

        widgets = {
            "plan": forms.Select(attrs={
                "class": "form-select"
            }),

            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),

            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Subscription Amount (Yearly)"
            }),

            "payment_reference": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "UPI / Bank Reference ID"
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError("Amount is required.")

        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")

        if amount > 100000:
            raise forms.ValidationError("Amount seems too large.")

        return amount

# =========================================================
# HUB USER CREATE FORM (SECURE)
# =========================================================

class HubUserCreateForm(forms.Form):

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm Password"
        })
    )

    # -------------------------------
    # CLEAN USERNAME
    # -------------------------------
    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        username = username.strip().lower()

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    # -------------------------------
    # CLEAN PASSWORD MATCH + STRENGTH
    # -------------------------------
    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:

            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

            # Django built-in strong password validator
            validate_password(password)

        return cleaned_data