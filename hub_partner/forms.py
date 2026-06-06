from django import forms
from admin_dashboard.models import ShippingCost

class HubShippingCostForm(forms.ModelForm):

    class Meta:
        model = ShippingCost

        fields = [
            "min_distance_km",
            "max_distance_km",
            "cost",
            "rider_earning",
            "platform_fee",
        ]

        widgets = {
            'min_distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'rider_earning': forms.NumberInput(attrs={'class': 'form-control'}),
            'platform_fee': forms.NumberInput(attrs={'class': 'form-control'}),
        }