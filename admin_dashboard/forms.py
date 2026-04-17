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


from django.forms import modelformset_factory
from .models import Product

from django import forms
from .models import Product, StockLog

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category','cost_price', 'price', 'discount_price',
            'stock_available', 'min_stock_level', 'size', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the product...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'cost_price':forms.NumberInput(attrs={'class':'form-control','placeholder':'Purchase cost(₹)'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Base Price (₹)'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sale Price (Optional)'}),
            'stock_available': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Current Quantity'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Alert at which quantity?'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1kg, 500ml'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
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

# Define the formset here
ProductImageFormSet = modelformset_factory(
    ProductImage,
    form=ProductImageForm,
    extra=5,      # Request up to 5 extra slots
    max_num=5,    # But never exceed 5 total
    can_delete=True,
)



#==========================================================



from .models import DeliveryHub
class DeliveryHubForm(forms.ModelForm):
    class Meta:
        model = DeliveryHub
        fields = ['name', 'latitude', 'longitude', 'max_delivery_radius_km']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_delivery_radius_km': forms.NumberInput(attrs={'class': 'form-control'}),
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
    
