from django import forms
from django.core.exceptions import ValidationError

from inventory.models import Inventory


class InventoryForm(forms.ModelForm):

    class Meta:

        model = Inventory

        fields = [
            'variant',
            'shop',
            'stock',
            'min_stock_level',
            'max_order_quantity',
            'mrp',
            'cost_price',
            'selling_price',
            'offer_label',
        ]

        widgets = {

            # ------------------------------------------------
            # VARIANT
            # ------------------------------------------------

            'variant': forms.Select(attrs={
                'class': 'form-select custom-input',
                'data-placeholder': 'Search product variant'
            }),

            # ------------------------------------------------
            # SHOP
            # ------------------------------------------------

            'shop': forms.Select(attrs={
                'class': 'form-select custom-input',
                'data-placeholder': 'Select shop'
            }),

            # ------------------------------------------------
            # STOCK
            # ------------------------------------------------

            'stock': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Current stock quantity',
                'min': 0
            }),

            # ------------------------------------------------
            # MIN STOCK
            # ------------------------------------------------

            'min_stock_level': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Low stock alert level',
                'min': 0
            }),

            # ------------------------------------------------
            # MAX ORDER
            # ------------------------------------------------

            'max_order_quantity': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Max quantity allowed per order',
                'min': 1
            }),

            'mrp': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Maximum Retail Price (MRP)',
                'step': '0.01',
                'min': 0
            }),

            # ------------------------------------------------
            # COST PRICE
            # ------------------------------------------------

            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Cost price',
                'step': '0.01',
                'min': 0
            }),

            # ------------------------------------------------
            # SELLING PRICE
            # ------------------------------------------------

            'selling_price': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Selling price',
                'step': '0.01',
                'min': 0
            }),

            'offer_label': forms.Select(attrs={
                'class': 'form-select custom-input',
            }),
        }

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ----------------------------------------------------
        # ACTIVE VARIANTS ONLY
        # ----------------------------------------------------

        self.fields['variant'].queryset = (

            self.fields['variant']
            .queryset
            .select_related('product')
            .filter(
                is_active=True,
                product__is_active=True
            )
            .order_by('product__name')
        )

        # ----------------------------------------------------
        # ACTIVE SHOPS ONLY
        # ----------------------------------------------------

        self.fields['shop'].queryset = (

            self.fields['shop']
            .queryset
            .filter(is_active=True)
            .select_related('hub')
            .order_by('name')
        )

        # ----------------------------------------------------
        # FRIENDLY LABELS
        # ----------------------------------------------------

        self.fields['variant'].label_from_instance = (

            lambda obj:
            f"{obj.product.name} • "
            f"{obj.quantity}{obj.unit}"
        )

        self.fields['shop'].label_from_instance = (

            lambda obj:
            f"{obj.name} • "
            f"{obj.get_shop_type_display()}"
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        variant = cleaned_data.get('variant')
        shop = cleaned_data.get('shop')

        stock = cleaned_data.get('stock')
        min_stock = cleaned_data.get('min_stock_level')

        max_order_qty = cleaned_data.get('max_order_quantity')
        mrp = cleaned_data.get('mrp')
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')

        # ----------------------------------------------------
        # STOCK VALIDATION
        # ----------------------------------------------------

        if stock is not None and stock < 0:

            raise ValidationError(
                "Stock cannot be negative."
            )

        if min_stock is not None and min_stock < 0:

            raise ValidationError(
                "Minimum stock level cannot be negative."
            )

        if max_order_qty is not None and max_order_qty <= 0:

            raise ValidationError(
                "Maximum order quantity must be greater than zero."
            )

        # ----------------------------------------------------
        # PRICE VALIDATION
        # ----------------------------------------------------

        if cost_price is not None and cost_price < 0:

            raise ValidationError(
                "Cost price cannot be negative."
            )

        if selling_price is not None and selling_price < 0:

            raise ValidationError(
                "Selling price cannot be negative."
            )
        
        if mrp is not None and mrp < 0:

            raise ValidationError(
                "MRP cannot be negative."
            )

        if (
            cost_price is not None and
            selling_price is not None and
            selling_price < cost_price
        ):

            raise ValidationError(
                "Selling price cannot be lower than cost price."
            )
        
        if (
            mrp is not None and
            selling_price is not None and
            mrp < selling_price
        ):

            raise ValidationError(
                "MRP cannot be lower than selling price."
            )
        # ----------------------------------------------------
        # DUPLICATE INVENTORY CHECK
        # ----------------------------------------------------

        if variant and shop:

            existing_inventory = Inventory.objects.filter(
                variant=variant,
                shop=shop
            )

            # Ignore self during edit
            if self.instance.pk:

                existing_inventory = existing_inventory.exclude(
                    pk=self.instance.pk
                )

            if existing_inventory.exists():

                raise ValidationError(
                    "Inventory already exists for this variant in this shop."
                )

        return cleaned_data