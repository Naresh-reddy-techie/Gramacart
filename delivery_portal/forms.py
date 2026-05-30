from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Delivery,
    DeliveryProfile,
    DeliveryStatus,
)


# =========================================================
# BASE MIXIN
# =========================================================

class StyledFormMixin:

    """
    Applies consistent production-ready UI classes.
    """

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():

            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):

                widget.attrs.update({
                    "class": "form-check-input"
                })

            elif isinstance(widget, forms.Select):

                widget.attrs.update({
                    "class": "form-select shadow-none"
                })

            elif isinstance(widget, forms.FileInput):

                widget.attrs.update({
                    "class": "form-control shadow-none"
                })

            else:

                widget.attrs.update({
                    "class": "form-control shadow-none"
                })


# =========================================================
# DELIVERY BOY CREATE
# =========================================================

class DeliveryBoyCreateForm(
    StyledFormMixin,
    forms.ModelForm
):

    username = forms.CharField(
        max_length=150
    )

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    first_name = forms.CharField(
        max_length=150,
        required=False
    )

    last_name = forms.CharField(
        max_length=150,
        required=False
    )

    email = forms.EmailField(
        required=False
    )

    class Meta:

        model = DeliveryProfile

        fields = [

            "phone_number",

            "hub",

            "vehicle_type",

            "is_active",
        ]

    # =====================================================
    # VALIDATIONS
    # =====================================================

    def clean_username(self):

        username = (
            self.cleaned_data
            .get("username")
            .strip()
            .lower()
        )

        if User.objects.filter(
            username=username
        ).exists():

            raise ValidationError(
                "Username already exists."
            )

        return username

    def clean_phone_number(self):

        phone = (
            self.cleaned_data
            .get("phone_number")
        )

        if phone:

            phone = phone.strip()

            if not phone.isdigit():

                raise ValidationError(
                    "Phone number must contain digits only."
                )

            if len(phone) < 10:

                raise ValidationError(
                    "Enter valid mobile number."
                )

        return phone

    # =====================================================
    # SAVE
    # =====================================================

    @transaction.atomic
    def save(self, commit=True):

        user = User.objects.create_user(

            username=self.cleaned_data["username"],

            password=self.cleaned_data["password"],

            email=self.cleaned_data.get(
                "email",
                ""
            ),

            first_name=self.cleaned_data.get(
                "first_name",
                ""
            ),

            last_name=self.cleaned_data.get(
                "last_name",
                ""
            ),
        )

        group, _ = Group.objects.get_or_create(
            name="DeliveryBoy"
        )

        user.groups.add(group)

        profile = super().save(
            commit=False
        )

        profile.user = user

        profile.is_online = False

        if commit:
            profile.save()

        return profile


# =========================================================
# DELIVERY PROFILE UPDATE
# =========================================================

class DeliveryProfileForm(
    StyledFormMixin,
    forms.ModelForm
):

    class Meta:

        model = DeliveryProfile

        fields = [

            "hub",

            "phone_number",

            "vehicle_type",

            "is_active",

            "is_online",
        ]

        labels = {

            "is_online": "Duty Status",

            "phone_number": "Mobile Number",
        }

    def clean_phone_number(self):

        phone = (
            self.cleaned_data
            .get("phone_number")
        )

        if phone:

            phone = phone.strip()

            if not phone.isdigit():

                raise ValidationError(
                    "Phone number must contain digits only."
                )

        return phone


# =========================================================
# DELIVERY BOY UPDATE
# =========================================================

class DeliveryBoyUpdateForm(
    StyledFormMixin,
    forms.ModelForm
):

    first_name = forms.CharField(
        max_length=150,
        required=False
    )

    last_name = forms.CharField(
        max_length=150,
        required=False
    )

    email = forms.EmailField(
        required=False
    )

    class Meta:

        model = DeliveryProfile

        fields = [

            "phone_number",

            "hub",

            "vehicle_type",

            "is_active",

            "is_online",
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.user:

            self.fields["first_name"].initial = (
                self.instance.user.first_name
            )

            self.fields["last_name"].initial = (
                self.instance.user.last_name
            )

            self.fields["email"].initial = (
                self.instance.user.email
            )

    @transaction.atomic
    def save(self, commit=True):

        profile = super().save(
            commit=False
        )

        user = profile.user

        user.first_name = self.cleaned_data.get(
            "first_name",
            ""
        )

        user.last_name = self.cleaned_data.get(
            "last_name",
            ""
        )

        user.email = self.cleaned_data.get(
            "email",
            ""
        )

        if commit:

            user.save()

            profile.save()

        return profile


# =========================================================
# PROOF UPLOAD
# =========================================================

class ProofUploadForm(
    StyledFormMixin,
    forms.ModelForm
):

    class Meta:

        model = Delivery

        fields = [

            "proof_photo",

            "tracking_notes",
        ]

        widgets = {

            "proof_photo": forms.FileInput(
                attrs={
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),

            "tracking_notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder":
                    "Example: Handed over to customer safely."
                }
            ),
        }


# =========================================================
# MANUAL ASSIGN
# =========================================================

class ManualAssignForm(forms.Form):

    delivery_boy = forms.ModelChoiceField(

        queryset=User.objects.none(),

        empty_label="-- Select Rider --",

        widget=forms.Select(
            attrs={
                "class": "form-select shadow-none"
            }
        )
    )

    def __init__(self, *args, **kwargs):

        hub = kwargs.pop(
            "hub",
            None
        )

        super().__init__(*args, **kwargs)

        queryset = User.objects.filter(

            groups__name="DeliveryBoy",

            delivery_profile__is_active=True,

            delivery_profile__is_online=True,

        ).select_related(
            "delivery_profile"
        )

        if hub:

            queryset = queryset.filter(
                delivery_profile__hub=hub
            )

        self.fields[
            "delivery_boy"
        ].queryset = queryset


# =========================================================
# DUTY TOGGLE
# =========================================================

class RiderDutyToggleForm(
    forms.ModelForm
):

    class Meta:

        model = DeliveryProfile

        fields = [

            "is_online"
        ]

        widgets = {

            "is_online": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "role": "switch",
                    "onchange": "this.form.submit();"
                }
            )
        }


# =========================================================
# DELIVERY ACCEPT
# =========================================================

class DeliveryAcceptForm(forms.Form):

    delivery_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop(
            "user",
            None
        )

        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        if not self.user:

            raise ValidationError(
                "Invalid rider."
            )

        if not hasattr(
            self.user,
            "delivery_profile"
        ):

            raise ValidationError(
                "Delivery profile missing."
            )

        profile = self.user.delivery_profile

        # ================================================
        # ONLINE CHECK
        # ================================================

        if not profile.is_online:

            raise ValidationError(
                "You must be ONLINE to accept deliveries."
            )

        # ================================================
        # DELIVERY CHECK
        # ================================================

        delivery_id = cleaned_data.get(
            "delivery_id"
        )

        try:

            delivery = Delivery.objects.select_related(
                "nearest_hub"
            ).get(
                id=delivery_id
            )

        except Delivery.DoesNotExist:

            raise ValidationError(
                "Delivery not found."
            )

        # ================================================
        # ALREADY CLAIMED
        # ================================================

        if delivery.delivery_boy:

            raise ValidationError(
                "Delivery already assigned."
            )

        # ================================================
        # STATUS CHECK
        # ================================================

        if delivery.status != DeliveryStatus.PACKED:

            raise ValidationError(
                "Delivery is not available."
            )

        # ================================================
        # HUB VALIDATION
        # ================================================

        if (
            profile.hub_id !=
            delivery.nearest_hub_id
        ):

            raise ValidationError(
                "This delivery belongs to another hub."
            )

        cleaned_data["delivery"] = delivery

        return cleaned_data


# =========================================================
# OTP VERIFY
# =========================================================

class DeliveryOTPVerifyForm(forms.Form):

    otp = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter 4-digit OTP",
                "autocomplete": "off",
            }
        )
    )

    def clean_otp(self):

        otp = (
            self.cleaned_data
            .get("otp")
            .strip()
        )

        if not otp.isdigit():

            raise ValidationError(
                "OTP must contain digits only."
            )

        return otp


# =========================================================
# COD CONFIRM
# =========================================================

class CODCollectionForm(forms.Form):

    cod_received = forms.BooleanField(
        required=True,
        label="I have collected COD amount from customer"
    )