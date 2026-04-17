from .models import CustomerProfile,Address,Order, Address
from django import forms

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['phone_number']
        widgets = {
            'phone_number':forms.NumberInput(attrs={'class':'form-control','placeholder':'Enter Mobile Number'}),
        }
        


import re
from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    # Explicitly set required=False so Django doesn't block the empty hidden fields
    state = forms.CharField(required=False, widget=forms.HiddenInput())
    country = forms.CharField(required=False, widget=forms.HiddenInput())
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput())
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Address
        fields = [
            'recipient_name', 'phone_number', 'address_line', 
            'landmark', 'city', 'state', 'country', 
            'pincode', 'address_type', 'latitude', 'longitude'
        ]
        widgets = {
            'recipient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Rama Rao'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit mobile number',
                'type': 'tel'
            }),
            'address_line': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'House No, Building, Street'
            }),
            'landmark': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Near Temple / School (Required)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Village/Town'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '6-digit PIN'
            }),
            'address_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        phone = re.sub(r'[\s\-]', '', str(phone))
        
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        
        if len(phone) not in [10, 12]:
            raise forms.ValidationError("Please enter a valid 10 or 12 digit phone number.")
            
        return phone

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')

        # Custom validation: Ensure the user actually tapped the map
        if not lat or not lon:
            raise forms.ValidationError("Please select a location on the map before saving.")
        
        # Safety Net: Fill in defaults if the JavaScript geocoder didn't respond in time
        if not cleaned_data.get('state'):
            cleaned_data['state'] = "Andhra Pradesh"
        if not cleaned_data.get('country'):
            cleaned_data['country'] = "India"
            
        return cleaned_data
# =======================================================


from payments.models import PaymentMethod

class CheckoutForm(forms.ModelForm):
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        empty_label=None,
        widget=forms.RadioSelect
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Additional instructions...'}),
        required=False
    )

    class Meta:
        model = Order
        fields = ['address', 'payment_method', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pop user from kwargs
        super().__init__(*args, **kwargs)

        # Dynamically filter addresses for this user
        if user:
            try:
                self.fields['address'].queryset = Address.objects.filter(customer__user=user)
            except Address.DoesNotExist:
                self.fields['address'].queryset = Address.objects.none()
        else:
            self.fields['address'].queryset = Address.objects.none()

#============================================
from .models import Rating

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['score', 'review']

        widgets = {
            'score': forms.HiddenInput(),  # we control via stars UI
            'review': forms.Textarea(attrs={
                'placeholder': 'Write your experience (optional but helpful)',
                'rows': 4,
                'class': 'form-control'
            }),
        }

    def clean_score(self):
        score = self.cleaned_data.get('score')
        if not score or score < 1 or score > 5:
            raise forms.ValidationError("Invalid rating")
        return score

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['score'].required = True
        self.fields['review'].required = False