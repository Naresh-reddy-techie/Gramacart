from django import forms
from django.contrib.auth.models import User, Group
from django.db import transaction
from .models import DeliveryProfile, Delivery

# ------------------- Mixins & Helpers -------------------

class StyledFormMixin:
    """Applies modern Bootstrap-style classes to all form fields automatically."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, (forms.Select, forms.RadioSelect)):
                field.widget.attrs.update({'class': 'form-select shadow-none'})
            else:
                field.widget.attrs.update({'class': 'form-control shadow-none'})

# ------------------- Partner Management -------------------

class DeliveryBoyCreateForm(StyledFormMixin, forms.ModelForm):
    """Handles joint creation of User and DeliveryProfile for onboarding."""
    username = forms.CharField(max_length=150, help_text="Used for login.")
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = DeliveryProfile
        fields = ['phone_number', 'hub', 'vehicle_type', 'is_active']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        """Uses atomic transaction to ensure User and Profile are created together."""
        with transaction.atomic():
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                password=self.cleaned_data['password'],
                email=self.cleaned_data.get('email', ''),
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', '')
            )
            
            # Auto-assign to the DeliveryBoy group
            group, _ = Group.objects.get_or_create(name='DeliveryBoy')
            user.groups.add(group)

            profile = super().save(commit=False)
            profile.user = user
            if commit:
                profile.save()
        return profile


class DeliveryProfileForm(StyledFormMixin, forms.ModelForm):
    """
    Updated to include the new Online/Offline status.
    """
    class Meta:
        model = DeliveryProfile
        # Add 'is_online' to the list below
        fields = ['hub', 'phone_number', 'vehicle_type', 'is_active', 'is_online']
        
        # Optional: Add a nice label so it looks good on the screen
        labels = {
            'is_online': 'Duty Status',
            'phone_number': 'WhatsApp Number',
        }

class DeliveryBoyUpdateForm(StyledFormMixin, forms.ModelForm):
    """Comprehensive form for Admin to update both Auth User and Profile info."""
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = DeliveryProfile
        fields = ['phone_number', 'hub', 'vehicle_type', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')
        
        if commit:
            with transaction.atomic():
                user.save()
                profile.save()
        return profile


# ------------------- Operations Forms -------------------

class ProofUploadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['proof_photo', 'tracking_notes']
        widgets = {
            'proof_photo': forms.FileInput(attrs={
                'accept': 'image/*',
                'capture': 'environment', # <--- Forces the back camera to open
                'class': 'form-control shadow-none'
            }),
            'tracking_notes': forms.Textarea(attrs={
                'rows': 2, 
                'placeholder': 'Example: Handed over to brother...'
            }),
        }

class ManualAssignForm(forms.Form):
    """Admin tool to override auto-dispatch and assign a specific rider."""
    delivery_boy = forms.ModelChoiceField(
        queryset=User.objects.filter(
            groups__name='DeliveryBoy',
            delivery_profile__is_active=True
        ).select_related('delivery_profile'),
        label="Select Available Partner",
        empty_label="-- Select a Rider --",
        widget=forms.Select(attrs={
            "class": "form-select shadow-none",
            "style": "border-radius: 12px;"
        })
    )

    def __init__(self, *args, **kwargs):
        hub = kwargs.pop('hub', None)
        super().__init__(*args, **kwargs)
        if hub:
            # Filter riders specifically from the village hub of the order
            self.fields['delivery_boy'].queryset = self.fields['delivery_boy'].queryset.filter(
                delivery_profile__hub=hub
            )

class RiderDutyToggleForm(forms.ModelForm):
    """
    A slim form just for the rider to toggle their duty status.
    """
    class Meta:
        model = DeliveryProfile
        fields = ['is_online']
        widgets = {
            'is_online': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'role': 'switch', # This makes it look like a toggle in Bootstrap 5
                'onchange': 'this.form.submit();' # Auto-submits when clicked
            })
        }

class DeliveryAcceptForm(forms.Form):
    """
    Used when a rider clicks 'Accept' on a pending order.
    Ensures they are actually online before allowing the assignment.
    """
    delivery_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.user and hasattr(self.user, 'delivery_profile'):
            if not self.user.delivery_profile.is_online:
                raise forms.ValidationError("You must be ONLINE to accept new orders.")
        return cleaned_data