from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .forms import InventoryForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Q,
    F,
    Sum,
    Count,
    DecimalField,
    ExpressionWrapper
)
from django.db.models.functions import Coalesce

from inventory.models import Inventory
from admin_dashboard.models import Category
from admin_dashboard.forms import StockLogForm


@login_required
def live_inventory(request):

    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    inventories = (
        Inventory.objects
        .select_related(
            'variant',
            'variant__product',
            'variant__product__category',
            'shop'
        )
        .order_by('-updated_at')
    )

    # =====================================================
    # SEARCH
    # =====================================================

    if query:
        inventories = inventories.filter(
            Q(variant__product__name__icontains=query) |
            Q(variant__product__description__icontains=query) |
            Q(shop__name__icontains=query)
        )

    # =====================================================
    # CATEGORY FILTER
    # =====================================================

    if category_id:
        inventories = inventories.filter(
            variant__product__category_id=category_id
        )

    # =====================================================
    # INVENTORY VALUE CALCULATION
    # =====================================================

    inventory_value_expression = ExpressionWrapper(
        F('stock') * F('selling_price'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )

    # =====================================================
    # STATS
    # =====================================================

    inventory_stats = inventories.aggregate(

        total_inventory_value=Coalesce(
            Sum(inventory_value_expression),
            Decimal('0.00')
        ),

        total_items=Count('id'),

        low_stock_count=Count(
            'id',
            filter=Q(
                stock__gt=0,
                stock__lte=F('min_stock_level')
            )
        ),

        out_of_stock_count=Count(
            'id',
            filter=Q(stock__lte=0)
        ),
    )

    # =====================================================
    # PAGINATION
    # =====================================================

    paginator = Paginator(inventories, 12)

    page_number = request.GET.get('page')

    inventory_page = paginator.get_page(page_number)

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        "inventories": inventory_page,

        "categories": Category.objects.all(),

        "stock_form": StockLogForm(),

        "total_inventory_value":
            inventory_stats['total_inventory_value'],

        "total_items":
            inventory_stats['total_items'],

        "low_stock_count":
            inventory_stats['low_stock_count'],

        "out_of_stock_count":
            inventory_stats['out_of_stock_count'],

        "query": query,
        "selected_category": category_id,
    }

    return render(
        request,
        "inventory/live_inventory.html",
        context
    )
# ============================================================
# ADD INVENTORY
# ============================================================

@login_required
def add_inventory(request):

    if request.method == 'POST':

        form = InventoryForm(request.POST)

        if form.is_valid():

            inventory = form.save(commit=False)

            # Prevent duplicate variant assignment
            exists = Inventory.objects.filter(
                variant=inventory.variant,
                shop=inventory.shop
            ).exists()

            if exists:

                messages.error(
                    request,
                    "Inventory already exists for this variant in this shop."
                )

                return redirect('inventory_list')

            inventory.save()

            messages.success(
                request,
                "Inventory created successfully."
            )

            return redirect('inventory_list')

    else:
        form = InventoryForm()

    return render(
        request,
        'inventory/inventory_form.html',
        {
            'form': form,
            'title': 'Add Inventory'
        }
    )


# ============================================================
# EDIT INVENTORY
# ============================================================

@login_required
def edit_inventory(request, pk):

    inventory = get_object_or_404(
        Inventory,
        pk=pk
    )

    if request.method == 'POST':

        form = InventoryForm(
            request.POST,
            instance=inventory
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Inventory updated successfully."
            )

            return redirect('inventory_list')

    else:

        form = InventoryForm(instance=inventory)

    return render(
        request,
        'inventory/inventory_form.html',
        {
            'form': form,
            'title': 'Edit Inventory'
        }
    )


# ============================================================
# INVENTORY LIST
# ============================================================

from django.db.models import Q, Sum, F
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from inventory.models import Inventory
from admin_dashboard.models import Shop, Product, ProductVariant, Category


@login_required
def inventory_list(request):

    inventory_items = Inventory.objects.select_related(
        'variant',
        'variant__product',
        'variant__product__category',
        'shop',
        'shop__hub'
    ).order_by('-updated_at')


    # ------------------------
    # SEARCH
    # ------------------------
    query = request.GET.get('q')
    if query:
        inventory_items = inventory_items.filter(
            Q(variant__product__name__icontains=query) |
            Q(shop__name__icontains=query)
        )


    # ------------------------
    # STATS (IMPORTANT FIX)
    # ------------------------
    low_stock_count = inventory_items.filter(
        stock__gt=0,
        stock__lte=F('min_stock_level')
    ).count()

    out_of_stock_count = inventory_items.filter(
        stock__lte=0
    ).count()

    total_products = inventory_items.values('variant').distinct().count()

    total_inventory_value = inventory_items.aggregate(
        total=Sum(F('stock') * F('selling_price'))
    )['total'] or 0


    # ------------------------
    # FILTER DATA
    # ------------------------
    hubs = []
    shops = Shop.objects.all()
    categories = Category.objects.all()


    return render(request, 'inventory/inventory_list.html', {
        'inventory_items': inventory_items,

        # filters
        'hubs': hubs,
        'shops': shops,
        'categories': categories,

        # stats
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_products': total_products,
        'total_inventory_value': total_inventory_value,
    })

# ============================================================
# DELETE INVENTORY
# ============================================================

@login_required
def delete_inventory(request, pk):

    inventory = get_object_or_404(
        Inventory,
        pk=pk
    )

    if request.method == 'POST':

        inventory.delete()

        messages.success(
            request,
            "Inventory deleted successfully."
        )

        return redirect('inventory_list')

    return render(
        request,
        'inventory/inventory_confirm_delete.html',
        {
            'inventory': inventory
        }
    )


# ============================================================
# UPDATE STOCK
# ============================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Inventory, StockLog


@login_required
@transaction.atomic
def update_stock(request, pk):

    inventory = get_object_or_404(
        Inventory.objects.select_related(
            'variant',
            'variant__product',
            'shop'
        ),
        pk=pk
    )

    if request.method == 'POST':

        try:
            change_amount = int(
                request.POST.get('change_amount', 0)
            )

        except (TypeError, ValueError):

            messages.error(
                request,
                "Invalid quantity entered."
            )

            return redirect('update_stock', pk=inventory.pk)

        reason = request.POST.get('reason', 'RESTOCK')
        note = request.POST.get('note', '').strip()

        # -----------------------------------
        # VALIDATION
        # -----------------------------------

        if change_amount == 0:

            messages.error(
                request,
                "Quantity cannot be zero."
            )

            return redirect('update_stock', pk=inventory.pk)

        # -----------------------------------
        # STOCK INCREASE
        # -----------------------------------

        try:

            if change_amount > 0:

                inventory.increase_stock(
                    qty=change_amount,
                    reason=reason,
                    note=note
                )

                messages.success(
                    request,
                    f"{change_amount} units added successfully."
                )

            # -----------------------------------
            # STOCK REDUCTION
            # -----------------------------------

            else:

                inventory.reduce_stock(
                    qty=abs(change_amount),
                    reason=reason,
                    note=note
                )

                messages.success(
                    request,
                    f"{abs(change_amount)} units reduced successfully."
                )

        except ValidationError as e:

            messages.error(
                request,
                str(e)
            )

        return redirect('inventory_list')

    return render(
        request,
        'inventory/update_stock.html',
        {
            'inventory': inventory
        }
    )