from .models import CustomerProfile,Address,Order, Address
from django import forms

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['phone_number']
        widgets = {
            'phone_number':forms.NumberInput(attrs={'class':'form-control','placeholder':'Enter Mobile Number'}),
        }
        

# =========================================================
# FORMS.py (PRODUCTION READY)
# =========================================================

import re

from django import forms

from .models import Address


# =========================================================
# ADDRESS FORM
# =========================================================

class AddressForm(forms.ModelForm):

    # =====================================================
    # HIDDEN FIELDS
    # =====================================================

    state = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    country = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    latitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )

    longitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )

    is_remote = forms.BooleanField(
        required=False
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        model = Address

        fields = [
            "recipient_name",
            "phone_number",
            "address_line",
            "landmark",
            "city",
            "state",
            "country",
            "pincode",
            "address_type",
            "latitude",
            "longitude",
            "is_remote",
            "is_default",
        ]

        widgets = {

            "recipient_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full Name"
            }),

            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "10 digit mobile number"
            }),

            "address_line": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "House no, street"
            }),

            "landmark": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nearby landmark"
            }),

            "city": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "pincode": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "address_type": forms.Select(attrs={
                "class": "form-select"
            }),
        }

    # =====================================================
    # PHONE VALIDATION
    # =====================================================

    def clean_phone_number(self):

        phone = re.sub(
            r"[\s\-]",
            "",
            str(
                self.cleaned_data.get(
                    "phone_number",
                    ""
                )
            )
        )

        if not re.match(
            r"^[6-9]\d{9}$",
            phone
        ):

            raise forms.ValidationError(
                "Enter valid mobile number."
            )

        return phone

    # =====================================================
    # PINCODE VALIDATION
    # =====================================================

    def clean_pincode(self):

        pincode = str(
            self.cleaned_data.get(
                "pincode",
                ""
            )
        ).strip()

        if not pincode.isdigit():

            raise forms.ValidationError(
                "Pincode must contain digits only."
            )

        if len(pincode) != 6:

            raise forms.ValidationError(
                "Enter valid 6 digit pincode."
            )

        return pincode

    # =====================================================
    # GLOBAL VALIDATION
    # =====================================================

    def clean(self):

        cleaned_data = super().clean()

        lat = cleaned_data.get("latitude")
        lon = cleaned_data.get("longitude")

        if lat is None or lon is None:

            raise forms.ValidationError(
                "Please select location on map."
            )

        cleaned_data["state"] = (
            cleaned_data.get("state")
            or "Andhra Pradesh"
        )

        cleaned_data["country"] = (
            cleaned_data.get("country")
            or "India"
        )

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