from django import forms


class ShopPayoutForm(forms.Form):

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    reference_number = forms.CharField(
        max_length=150
    )

    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows":3
            }
        )
    )