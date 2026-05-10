from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.urls import reverse
from delivery_portal.models import Delivery, DeliveryProfile
# -------------- DASHBOARD -----------------------
"""
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Sum, Q
from shop.models import Order, Product 
from payments.models import Payment
from admin_dashboard.models import CompanyInfo
from delivery_portal.models import Delivery, DeliveryProfile
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    today = timezone.now().date()

    # 1. Company & User Context
    company_info = CompanyInfo.objects.first()
    
    # 2. Orders Stats
    orders = Order.objects.all()
    # Note: Using your status choices from the choice list
    pending_orders = orders.filter(status='pending').count()
    completed_orders = orders.filter(status='delivered').count()
    
    # 3. Live Village Logistics (FIXED: Using placed_at instead of created_at)
    active_orders = Order.objects.filter(
        status__in=['pending', 'processing', 'shipped']
    ).select_related('user', 'address').order_by('-placed_at')[:10] 

    # 4. Inventory Intelligence
    all_products = Product.objects.all()
    total_products = all_products.count()
    # Assuming Product has a stock field; adjust 'stock' to your actual field name if needed
    low_stock_count = all_products.filter(stock_available__lte=5, stock_available__gt=0).count()
    out_of_stock_count = all_products.filter(stock_available=0).count()

    # 5. Financial Core (FIXED: Check your Payment model field for date)
    total_revenue = Payment.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
    
    # Assuming Payment has 'created_at'. If it crashes there, check the Payment model fields!
    revenue_today = Payment.objects.filter(
        status='success', 
        created_at__date=today # Change to timestamp__date if Payment uses timestamp
    ).aggregate(total=Sum('amount'))['total'] or 0

    # 6. Delivery Fleet Status
    delivery_profiles = DeliveryProfile.objects.select_related('user', 'hub')
    active_riders = delivery_profiles.filter(is_active=True).count()
    
    # 7. Customer Intelligence
    total_customers = User.objects.exclude(is_staff=True).count()
    new_customers_today = User.objects.filter(date_joined__date=today).count()

    context = {
        'company_info': company_info,
        'last_login': request.user.last_login,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'low_stock_count': low_stock_count,
        'active_riders': active_riders,
        'active_orders': active_orders,
        'total_products': total_products,
        'out_of_stock_count': out_of_stock_count,
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
    }

    return render(request, 'admin_dashboard/dashboard.html', context)
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.db.models import (
    Sum,
    Count,
    Q,
    F,
    DecimalField
)
from django.shortcuts import render
from django.utils import timezone

from shop.models import Order
from payments.models import Payment

from inventory.models import Inventory

from admin_dashboard.models import (
    CompanyInfo,
    ShopLedger,
)

from delivery_portal.models import DeliveryProfile


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@login_required
def dashboard(request):

    today = timezone.now().date()

    # ========================================================
    # COMPANY INFO
    # ========================================================

    company_info = (
        CompanyInfo.objects
        .only('id', 'name', 'logo')
        .first()
    )

    # ========================================================
    # ORDER ANALYTICS
    # ========================================================

    orders = (
        Order.objects
        .select_related('user', 'address')
    )

    order_stats = orders.aggregate(

        pending_orders=Count(
            'id',
            filter=Q(status='pending')
        ),

        processing_orders=Count(
            'id',
            filter=Q(status='processing')
        ),

        shipped_orders=Count(
            'id',
            filter=Q(status='shipped')
        ),

        delivered_orders=Count(
            'id',
            filter=Q(status='delivered')
        ),

        cancelled_orders=Count(
            'id',
            filter=Q(status='cancelled')
        ),

        active_orders=Count(
            'id',
            filter=Q(
                status__in=[
                    'pending',
                    'processing',
                    'shipped'
                ]
            )
        )
    )

    recent_orders = (
        orders
        .filter(
            status__in=[
                'pending',
                'processing',
                'shipped'
            ]
        )
        .order_by('-placed_at')[:10]
    )

    # ========================================================
    # INVENTORY ANALYTICS
    # ========================================================

    inventories = (
        Inventory.objects
        .select_related(
            'variant',
            'variant__product',
            'shop'
        )
    )

    inventory_stats = inventories.aggregate(

        total_inventory_items=Count('id'),

        total_products=Count(
            'variant__product',
            distinct=True
        ),

        total_variants=Count(
            'variant',
            distinct=True
        ),

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

        total_stock_units=Sum('stock'),

        total_inventory_value=Sum(
            F('stock') * F('cost_price'),
            output_field=DecimalField(
                max_digits=14,
                decimal_places=2
            )
        )
    )

    low_stock_items = (
        inventories
        .filter(
            stock__gt=0,
            stock__lte=F('min_stock_level')
        )
        .order_by('stock')[:10]
    )

    # ========================================================
    # PAYMENT ANALYTICS
    # ========================================================

    successful_payments = (
        Payment.objects
        .filter(status='success')
    )

    payment_stats = successful_payments.aggregate(

        total_revenue=Sum('amount'),

        revenue_today=Sum(
            'amount',
            filter=Q(created_at__date=today)
        )
    )

    # ========================================================
    # PROFIT ANALYTICS
    # ========================================================

    ledger_stats = ShopLedger.objects.aggregate(

        total_profit=Sum('profit'),

        unsettled_entries=Count(
            'id',
            filter=Q(is_settled=False)
        )
    )

    # ========================================================
    # DELIVERY NETWORK ANALYTICS
    # ========================================================

    rider_stats = DeliveryProfile.objects.aggregate(

        active_riders=Count(
            'id',
            filter=Q(is_active=True)
        ),

        inactive_riders=Count(
            'id',
            filter=Q(is_active=False)
        )
    )

    # ========================================================
    # CUSTOMER ANALYTICS
    # ========================================================

    customer_stats = User.objects.aggregate(

        total_customers=Count(
            'id',
            filter=Q(is_staff=False)
        ),

        new_customers_today=Count(
            'id',
            filter=Q(
                is_staff=False,
                date_joined__date=today
            )
        )
    )

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context = {

        # Company
        'company_info': company_info,

        # Orders
        'pending_orders':
            order_stats.get('pending_orders', 0),

        'processing_orders':
            order_stats.get('processing_orders', 0),

        'shipped_orders':
            order_stats.get('shipped_orders', 0),

        'completed_orders':
            order_stats.get('delivered_orders', 0),

        'cancelled_orders':
            order_stats.get('cancelled_orders', 0),

        'active_orders_count':
            order_stats.get('active_orders', 0),

        'recent_orders':
            recent_orders,

        # Inventory
        'total_inventory_items':
            inventory_stats.get('total_inventory_items', 0),

        'total_products':
            inventory_stats.get('total_products', 0),

        'total_variants':
            inventory_stats.get('total_variants', 0),

        'low_stock_count':
            inventory_stats.get('low_stock_count', 0),

        'out_of_stock_count':
            inventory_stats.get('out_of_stock_count', 0),

        'total_stock_units':
            inventory_stats.get('total_stock_units') or 0,

        'total_inventory_value':
            inventory_stats.get('total_inventory_value') or 0,

        'low_stock_items':
            low_stock_items,

        # Revenue
        'total_revenue':
            payment_stats.get('total_revenue') or 0,

        'revenue_today':
            payment_stats.get('revenue_today') or 0,

        # Profit
        'total_profit':
            ledger_stats.get('total_profit') or 0,

        'unsettled_entries':
            ledger_stats.get('unsettled_entries', 0),

        # Riders
        'active_riders':
            rider_stats.get('active_riders', 0),

        'inactive_riders':
            rider_stats.get('inactive_riders', 0),

        # Customers
        'total_customers':
            customer_stats.get('total_customers', 0),

        'new_customers_today':
            customer_stats.get('new_customers_today', 0),
    }

    return render(
        request,
        'admin_dashboard/dashboard.html',
        context
    )
#================================================


from django.contrib.auth.models import Group, Permission
from django.contrib import messages

from django.contrib.auth.models import Group, Permission

@login_required
def create_custom_group(request):
    # Fetch all permissions to show on the "Create" page
    all_permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label')

    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        selected_perm_ids = request.POST.getlist('permissions') # Get checked permissions
        
        if group_name:
            # 1. Create the Group
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                # 2. Assign the permissions immediately
                if selected_perm_ids:
                    group.permissions.set(selected_perm_ids)
                
                messages.success(request, f"Role '{group_name}' created with selected permissions!")
                return redirect('manage_groups')
            else:
                messages.error(request, f"The role '{group_name}' already exists.")
        else:
            messages.error(request, "Role name is required.")

    return render(request, 'admin_dashboard/create_group.html', {
        'all_permissions': all_permissions
    })

def edit_group(request, pk):
    group = get_object_or_404(Group, pk=pk)
    all_permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label')

    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        selected_perm_ids = request.POST.getlist('permissions')
        
        if group_name:
            group.name = group_name
            group.save()
            group.permissions.set(selected_perm_ids)
            messages.success(request, f"Updated {group_name} successfully!")
            return redirect('manage_groups')

    # This is the "Magic" line that pre-checks the boxes
    current_perms = group.permissions.values_list('id', flat=True)

    return render(request, 'admin_dashboard/edit_group.html', {
        'group': group,
        'all_permissions': all_permissions,
        'current_perms': current_perms # Send this to the template
    })
#=====================================================
from django.contrib.auth.models import Group

@login_required
def manage_groups(request):
    # Fetch all roles/groups created in the system
    groups = Group.objects.all().order_by('name')
    
    return render(request, 'admin_dashboard/manage_groups.html', {
        'groups': groups
    })

from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404

@login_required
def delete_group(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        group_delete_name = group.name
        group.delete()
        messages.warning(request, f"Role '{group_delete_name}' has been removed.")
    return redirect('manage_groups')

@login_required
def edit_group_permissions(request, pk):
    group = get_object_or_404(Group, pk=pk)
    # Fetch all available permissions in the system
    all_permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label')

    if request.method == 'POST':
        # Get the list of permission IDs from the checkboxes
        permission_ids = request.POST.getlist('permissions')
        group.permissions.set(permission_ids) # This updates the role's powers
        messages.success(request, f"Permissions updated for {group.name}")
        return redirect('manage_groups')

    # Get IDs of permissions the group already has to pre-check boxes
    current_permissions = group.permissions.values_list('id', flat=True)

    return render(request, 'admin_dashboard/edit_group_permissions.html', {
        'group': group,
        'all_permissions': all_permissions,
        'current_permissions': current_permissions
    })
#------------------------------------------------------------------

from django.contrib.auth.models import User, Group

@login_required
def assign_group_to_users(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Fetch all active users to show in the list
    all_users = User.objects.filter(is_active=True).order_by('username')
    
    if request.method == 'POST':
        # Get the list of user IDs from the checkboxes
        user_ids = request.POST.getlist('selected_users')
        # Update the group's members
        group.user_set.set(user_ids)
        
        messages.success(request, f"Users updated for role: {group.name}")
        return redirect('manage_groups')

    # Get IDs of users currently in this group
    current_member_ids = group.user_set.values_list('id', flat=True)

    return render(request, 'admin_dashboard/assign_group_to_users.html', {
        'group': group,
        'all_users': all_users,
        'current_member_ids': current_member_ids,
    })
#=======================================================
from .models import Category
from .forms import CategoryForm

def superuser_required(view_func):
    decorated_view = login_required(user_passes_test(lambda u:u.is_superuser)(view_func))
    return decorated_view
#============================================================
from .models import CompanyInfo
from .forms import CompanyInfoForm

def company_info_update(request):
    # Try to get the first CompanyInfo object, or None if doesn't exist
    company_info = CompanyInfo.objects.first()

    if request.method == 'POST':
        form = CompanyInfoForm(request.POST, request.FILES, instance=company_info)
        if form.is_valid():
            form.save()
            messages.success(request, "Company information updated successfully.")
            return redirect('company_info_update')
    else:
        form = CompanyInfoForm(instance=company_info)

    context = {
        'form': form,
    }
    return render(request, 'admin_dashboard/company_info_form.html', context)



#------------ADD,EDIT,LIST,DELETE Categories---------------------

@superuser_required
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'Category added succesfully...')
            return redirect('list_category')
    else:
        form = CategoryForm()
    return render(request,'Category/add_category.html',{'form':form})

def edit_category(request,id):
    category = get_object_or_404(Category,id=id)
    if request.method == 'POST':
        form = CategoryForm(request.POST,instance=category)
        if form.is_valid():
            form.save()
            messages.success(request,"Category updated successfully")
            return redirect('list_category')
    else:
        form = CategoryForm(instance=category)
    return render(request,'Category/edit_category.html',{'form':form})


def list_category(request):
    all_categories = Category.objects.all().order_by('-id')
    paginator = Paginator(all_categories,7)
    page_num = request.GET.get('page')
    categories = paginator.get_page(page_num)
    return render(request,'Category/list_category.html',{'categories':categories})


def delete_category(request,id):
    category = get_object_or_404(Category,id=id)
    if request.method == 'POST':
        category.delete()
        messages.error(request,"Categroy deleted succesfully.")
        return redirect('list_category')
      

#-----------------------------------------------------------------

#---------------ADD,EDIT,DELETE,LIST Products--------------------

from django.core.files.storage import default_storage

from .forms import ProductForm
from .models import Product, ProductImage
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from .models import Product
from .forms import (
    ProductForm,
    ProductVariantFormSet,
    ProductImageFormSet,
)


@transaction.atomic
def add_product(request):

    if request.method == 'POST':

        form = ProductForm(request.POST)

        variant_formset = ProductVariantFormSet(
            request.POST,
            prefix='variants'
        )

        image_formset = ProductImageFormSet(
            request.POST,
            request.FILES,
            prefix='images'
        )

        if (
            form.is_valid()
            and variant_formset.is_valid()
            and image_formset.is_valid()
        ):

            # =================================================
            # SAVE PRODUCT
            # =================================================

            product = form.save()

            # =================================================
            # SAVE VARIANTS
            # =================================================

            variants = variant_formset.save(commit=False)

            for variant in variants:
                variant.product = product
                variant.save()

            # delete removed variants
            for obj in variant_formset.deleted_objects:
                obj.delete()

            # =================================================
            # SAVE IMAGES
            # =================================================

            images = image_formset.save(commit=False)

            for image in images:
                image.product = product
                image.save()

            for obj in image_formset.deleted_objects:
                obj.delete()

            messages.success(request,"Product created successfully.")

            return redirect('list_product')

        else:
            print(form.errors)
            print(variant_formset.errors)
            print(image_formset.errors)

            messages.error(request,"Please correct the errors below.")

    else:

        form = ProductForm()

        variant_formset = ProductVariantFormSet(prefix='variants')

        image_formset = ProductImageFormSet(prefix='images')

    context = {
        'form': form,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
    }

    return render(request,'Product/add_product.html',context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from .models import Product

from .forms import (
    ProductForm,
    ProductVariantFormSet,
    ProductImageFormSet
)


@transaction.atomic
def edit_product(request, slug):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            'variants',
            'product_images'
        ),
        slug=slug
    )

    # =====================================================
    # POST
    # =====================================================

    if request.method == 'POST':

        form = ProductForm(
            request.POST,
            instance=product
        )

        variant_formset = ProductVariantFormSet(
            request.POST,
            instance=product,
            prefix='variants'
        )

        image_formset = ProductImageFormSet(
            request.POST,
            request.FILES,
            instance=product,
            prefix='images'
        )

        if (
            form.is_valid()
            and variant_formset.is_valid()
            and image_formset.is_valid()
        ):

            # =========================================
            # SAVE PRODUCT
            # =========================================

            product = form.save()

            # =========================================
            # SAVE VARIANTS
            # =========================================

            variants = variant_formset.save(commit=False)

            for variant in variants:
                variant.product = product
                variant.save()

            for deleted_variant in variant_formset.deleted_objects:
                deleted_variant.delete()

            # =========================================
            # SAVE IMAGES
            # =========================================

            images = image_formset.save(commit=False)

            for image in images:
                image.product = product
                image.save()

            for deleted_image in image_formset.deleted_objects:
                deleted_image.delete()

            messages.success(
                request,
                "Product updated successfully."
            )

            return redirect('list_product')

        else:

            print(form.errors)
            print(variant_formset.errors)
            print(image_formset.errors)

            messages.error(
                request,
                "Please correct the errors below."
            )

    # =====================================================
    # GET
    # =====================================================

    else:

        form = ProductForm(
            instance=product
        )

        variant_formset = ProductVariantFormSet(
            instance=product,
            prefix='variants'
        )

        image_formset = ProductImageFormSet(
            instance=product,
            prefix='images'
        )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        'product': product,
        'form': form,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
    }

    return render(
        request,
        'Product/edit_product.html',
        context
    )




def delete_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('list_product')
    return render(request, 'Product/delete_product.html', {'product': product})


def list_product(request):
    product_list = Product.objects.all().order_by('-id')  # newest first

    # Set pagination: 10 products per page
    paginator = Paginator(product_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
    }
    return render(request, 'Product/list_product.html', context)
#--------------------------------------------------------


from .models import DeliveryHub
from .forms import DeliveryHubForm

def list_delivery_hubs(request):
    hubs = DeliveryHub.objects.all()
    return render(request, 'admin_dashboard/list_delivery_hubs.html', {'hubs': hubs})


def add_delivery_hub(request):
    if request.method == 'POST':
        form = DeliveryHubForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Delivery Hub added successfully.")
            return redirect('list_delivery_hubs')
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = DeliveryHubForm()

    return render(request, 'admin_dashboard/add_delivery_hub.html', {'form': form})


def edit_delivery_hub(request, pk):
    hub = get_object_or_404(DeliveryHub, pk=pk)

    if request.method == 'POST':
        form = DeliveryHubForm(request.POST, instance=hub)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Delivery Hub updated successfully.")
            return redirect('list_delivery_hubs')
        else:
            messages.error(request, "⚠️ Please fix the form errors.")
    else:
        initial = {
            'latitude': hub.latitude,
            'longitude': hub.longitude,
        }
        form = DeliveryHubForm(instance=hub, initial=initial)

    return render(request, 'admin_dashboard/edit_delivery_hub.html', {'form': form, 'hub': hub})

def delete_delivery_hub(request, pk):
    hub = get_object_or_404(DeliveryHub, pk=pk)

    if request.method == 'POST':
        hub.delete()
        messages.success(request, "🗑️ Delivery Hub deleted.")
        return redirect('list_delivery_hubs')

    return render(request, 'admin_dashboard/delete_delivery_hub.html', {'hub': hub})



#==================================================

from .models import ShippingCost, DeliveryHub
from .forms import ShippingCostForm

# List all shipping costs
def shipping_cost_list(request):
    shipping_costs = ShippingCost.objects.all()
    return render(request, 'admin_dashboard/shipping_cost_list.html', {
        'shipping_costs': shipping_costs
    })

# Add a new shipping cost
def add_shipping_cost(request):
    if request.method == 'POST':
        form = ShippingCostForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Shipping cost added successfully!")
            return redirect('shipping_cost_list')
    else:
        form = ShippingCostForm()

    return render(request, 'admin_dashboard/shipping_cost_form.html', {'form': form})

# Update an existing shipping cost
def update_shipping_cost(request, id):
    shipping_cost = get_object_or_404(ShippingCost, id=id)

    if request.method == 'POST':
        form = ShippingCostForm(request.POST, hubs=DeliveryHub.objects.all())
        if form.is_valid():
            shipping_cost.delivery_hub = form.cleaned_data['delivery_hub']
            shipping_cost.min_distance_km = form.cleaned_data['min_distance_km']
            shipping_cost.max_distance_km = form.cleaned_data['max_distance_km']
            shipping_cost.cost = form.cleaned_data['customer_fee']
            shipping_cost.rider_earning = form.cleaned_data['rider_earning']
            shipping_cost.platform_fee = form.cleaned_data['platform_fee']
            shipping_cost.save()

            messages.success(request, "Shipping cost updated successfully!")
            return redirect('shipping_cost_list')
    else:
        form = ShippingCostForm(hubs=DeliveryHub.objects.all())
        form.set_shipping_costs(
            customer_fee=shipping_cost.cost,
            rider_earning=shipping_cost.rider_earning,
            platform_fee=shipping_cost.platform_fee
        )
    
    return render(request, 'admin_dashboard/shipping_cost_form.html', {'form': form})

# Delete an existing shipping cost
def delete_shipping_cost(request, id):
    shipping_cost = get_object_or_404(ShippingCost, id=id)
    if request.method == 'POST':
        shipping_cost.delete()
        messages.success(request, "Shipping cost deleted successfully!")
        return redirect('shipping_cost_list')
    return render(request, 'admin_dashboard/shipping_cost_confirm_delete.html', {
        'shipping_cost': shipping_cost
    })


#=====================================
"""
from .utils import haversine
from .utils import haversine

def is_delivery_available(customer_lat, customer_lng):
    hubs = DeliveryHub.objects.all()
    for hub in hubs:
        distance = haversine(
            float(customer_lat),
            float(customer_lng),
            float(hub.latitude),
            float(hub.longitude)
        )
        if distance <= hub.max_delivery_radius_km:
            return True
    return False



def check_pincode_delivery(request):
    delivery_available = None

    if request.method == 'POST':
        customer_lat = float(request.POST.get('latitude'))
        customer_lng = float(request.POST.get('longitude'))
        delivery_available = is_delivery_available(customer_lat, customer_lng)

    return render(request, 'admin_dashboard/check_delivery.html', {
        'delivery_available': delivery_available,
    })
"""
#----------------------------------------------------------------

from payments.models import PaymentMethod
from .forms import PaymentMethodForm

@superuser_required
def payment_methods_list(request):
    methods = PaymentMethod.objects.all().order_by('sort_order', 'name')
    return render(request, 'admin_dashboard/payment_methods_list.html', {'payment_methods': methods})

@superuser_required
def payment_method_add(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse('payment_methods_list'))
        print(form.errors)
    else:
        form = PaymentMethodForm()
    context ={
        'form':form,
        'title':'Add Payment Method',
        'basic_fields':['name','display_name','is_active','sort_order'],
    }
    return render(request, 'admin_dashboard/payment_method_form.html',context)
    
@superuser_required
def payment_method_edit(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            return redirect(reverse('payment_methods_list'))
    else:
        form = PaymentMethodForm(instance=method)
    return render(request, 'admin_dashboard/payment_method_form.html', {
        'form': form,
        'title': 'Edit Payment Method',
    })

@superuser_required
def payment_method_delete(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == 'POST':
        method.delete()
        return redirect(reverse('payment_methods_list'))
    return render(request, 'admin_dashboard/payment_method_confirm_delete.html', {'object': method})

#===============================================================

from django.utils.timezone import now
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
import json
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from django.db.models import Q, Sum
from django.core.paginator import Paginator

# Import your models here
# from .models import Order, Delivery, DeliveryProfile

@staff_member_required
def live_orders_admin(request):
    """
    VIEW 1: The UI Skeleton
    Renders the main dashboard page.
    """
    delivery_boys = DeliveryProfile.objects.filter(is_active=True).select_related('user')
    return render(request, 'admin_dashboard/orders.html', {
        'delivery_boys': delivery_boys
    })
@staff_member_required
def admin_order_list_json(request, order_number=None):
    # 1. SINGLE ORDER DETAIL (Deep Dive)
    if order_number:
        order = get_object_or_404(Order.objects.select_related('user', 'address'), order_number=order_number)
        return JsonResponse({
            'order_number': order.order_number,
            'items': [
                {
                    'product_name': item.product.name,
                    'product_size': item.product.size,
                    'quantity': item.quantity,
                    'image_url': item.product.product_images.first().image.url if item.product.product_images.exists() else None,
                    'item_total': float(item.price * item.quantity)
                } for item in order.items.all()
            ]
        })

    # 2. THE OPERATIONAL BUCKETS
    status_filter = request.GET.get('status', 'live') 
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)

    # Base Query: Select related/prefetch to avoid N+1 database queries
    order_list = Order.objects.select_related('user', 'address', 'delivery').prefetch_related('items__product').order_by('-placed_at')

    # --- UPDATED FILTERING LOGIC ---
    if status_filter == 'live':
        # STAGE 1: New Customer Orders (Must show 'pending' so Admin can see them first)
        order_list = order_list.filter(status='pending')

    elif status_filter == 'packed':
        # STAGE 2: Packed & Ready (The Radar)
        # Show orders that are packed but don't have a rider assigned yet
        order_list = order_list.filter(status='packed', delivery__delivery_boy__isnull=True)
    
    elif status_filter == 'tracking':
        # STAGE 3: In Transit
        order_list = order_list.filter(status='out_for_delivery')
    
    elif status_filter == 'history':
        # STAGE 4: Completed or Dead
        order_list = order_list.filter(status__in=['delivered', 'cancelled', 'rejected'])

    # Search Logic
    if search_query:
        order_list = order_list.filter(
            Q(order_number__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(address__phone_number__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(order_list, 12)
    page_obj = paginator.get_page(page_number)

    # Build Response Data
    data = []
    for order in page_obj:
        data.append({
            'order_number': order.order_number,
            'customer': order.user.get_full_name() if order.user else 'Guest',
            'status': order.get_status_display(),
            'status_code': order.status,
            'total': float(order.total),
            'village_cluster': order.address.city if order.address else 'Direct Hub',
            'address': {
                'address_line': order.address.address_line if order.address else 'N/A',
                'landmark': getattr(order.address, 'landmark', 'N/A'),
                'phone': order.address.phone_number if order.address else 'N/A'
            },
            'items': [
                {
                    'product_name': i.product.name,
                    'product_size': i.product.size,
                    'quantity': i.quantity,
                    'image_url': i.product.product_images.first().image.url if i.product.product_images.exists() else None
                } for i in order.items.all()
            ]
        })

    # Top HUD Stats
    today = now().date()
    return JsonResponse({
        'orders': data,
        'total_pages': paginator.num_pages,
        'live_count': Order.objects.filter(status='pending').count(),
        'packed_count': Order.objects.filter(status='packed', delivery__delivery_boy__isnull=True).count(),
        'tracking_count': Order.objects.filter(status='out_for_delivery').count(),
        'today_revenue': float(Order.objects.filter(placed_at__date=today, status='delivered').aggregate(s=Sum('total'))['s'] or 0)
    })

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from shop.models import Order
"""
@staff_member_required
def mark_order_as_packed(request, order_number):
    if request.method == 'POST':
        # 1. Get the order or return 404
        order = get_object_or_404(Order, order_number=order_number)
        
        # 2. Update the status
        order.status = 'packed'
        order.save()
        
        # 3. Return success to the JavaScript
        return JsonResponse({
            'success': True, 
            'message': f'Order {order_number} marked as packed.'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

"""
from decimal import Decimal
from django.db import transaction
from .utils import haversine  # We need this to find which slab to use

@staff_member_required
def mark_order_as_packed(request, order_number):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_number=order_number)
        
        with transaction.atomic():
            order.status = 'PACKED'
            order.save()
            
            delivery, created = Delivery.objects.get_or_create(order=order)
            delivery.status = DeliveryStatus.PACKED
            
            if order.address:
                from admin_dashboard.models import DeliveryHub, ShippingCost
                
                # 1. STRONGER HUB SEARCH
                # Clean the city name to remove accidental spaces
                clean_city = order.address.city.strip()
                hub = DeliveryHub.objects.filter(name__icontains=clean_city).first()
                
                # FALLBACK: If city name doesn't match, grab the first active hub
                # This ensures the order IS NOT NULL so it shows up on the radar
                if not hub:
                    hub = DeliveryHub.objects.filter(is_active=True).first()

                if hub:
                    delivery.nearest_hub = hub
                    
                    # 2. GET DISTANCE
                    dist = haversine(hub.latitude, hub.longitude, 
                                     order.address.latitude, order.address.longitude)
                    delivery.distance_km = Decimal(str(round(dist, 2)))

                    # 3. DYNAMIC PRICING FROM ADMIN TABLE
                    # Find the exact slab the admin set for this hub and distance
                    pricing_tier = ShippingCost.objects.filter(
                        delivery_hub=hub,
                        min_distance_km__lte=dist,
                        max_distance_km__gte=dist
                    ).first()

                    if pricing_tier:
                        delivery.rider_earning = pricing_tier.rider_earning
                    else:
                        # If admin forgot to add a slab, we use 0 or a base rate 
                        # so the order is still visible
                        delivery.rider_earning = 0 

            delivery.save()
        
        return JsonResponse({'success': True})
    
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json
from delivery_portal.models import DeliveryStatus
@require_POST
@staff_member_required
def update_order_status_ajax(request):
    try:
        data = json.loads(request.body)
        order_num = data.get('order_number')
        rider_id = data.get('delivery_boy_id')

        # 1. Fetch the Order 
        # (This order already has the 'shipping_cost' set by the Admin)
        order = get_object_or_404(Order, order_number=order_num)

        with transaction.atomic():
            if rider_id:
                # 2. Identify the Rider and their Hub
                profile = get_object_or_404(DeliveryProfile, id=rider_id)
                hub = profile.hub
                
                # 3. Get or Create the Delivery record
                delivery, created = Delivery.objects.get_or_create(order=order)
                
                # 4. LOOKUP THE ADMIN'S PRICING TIER
                # We find the tier in this Hub where the 'cost' matches the 
                # 'shipping_cost' the Admin assigned to the order.
                pricing_tier = ShippingCost.objects.filter(
                    delivery_hub=hub,
                    cost=order.shipping_cost
                ).first()

                # 5. Update Delivery Logistics
                delivery.delivery_boy = profile.user
                delivery.status = DeliveryStatus.ASSIGNED
                delivery.assigned_at = timezone.now()
                delivery.nearest_hub = hub
                
                # 6. SET DYNAMIC FINANCIALS FROM THE TIER
                if pricing_tier:
                    # This ensures the rider earns exactly what the Admin defined for this cost bracket
                    delivery.rider_earning = pricing_tier.rider_earning
                    # Optional: Store the distance range for the rider's info
                    delivery.distance_km = Decimal(str(pricing_tier.max_distance_km)) 
                else:
                    # Fallback: if no tier matches exactly, use a percentage
                    delivery.rider_earning = order.shipping_cost * Decimal('0.70')

                delivery.save()
                
                # 7. Finalize Order Status
                order.status = 'out_for_delivery'
                order.save()

        return JsonResponse({
            'success': True, 
            'message': f'Assigned to {profile.user.username}. Rider Earning: ₹{delivery.rider_earning}'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@require_POST
@staff_member_required
def reject_order_ajax(request):
    """
    VIEW 4: The Cancellation Handler
    Safely cancels orders with a reason.
    """
    try:
        data = json.loads(request.body)
        order_num = data.get('order_number')
        reason = data.get('reason', 'Out of Stock')

        order = get_object_or_404(Order, order_number=order_num)
        order.status = 'cancelled'
        order.rejection_reason = reason # Make sure this field exists in your Order model
        order.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@staff_member_required
def order_print_view(request, order_number):
    """Renders printable slip."""
    order = get_object_or_404(Order.objects.select_related('address', 'user'), order_number=order_number)
    return render(request, 'admin_dashboard/order_print.html', {'order': order})

import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- Header & Branding ---
    p.setFont("Helvetica-Bold", 24)
    p.setFillColor(colors.hexColor("#00b359")) # GramaCart Green
    p.drawString(1*inch, height - 1*inch, "GramaCart")
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.black)
    p.drawString(1*inch, height - 1.25*inch, "All essentials one cart.")

    # --- Invoice Info ---
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width - 1*inch, height - 1*inch, f"INVOICE: #{order.order_number}")
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 1*inch, height - 1.2*inch, f"Date: {order.created_at.strftime('%d %b %Y')}")

    # --- Bill To Section ---
    p.line(1*inch, height - 1.6*inch, width - 1*inch, height - 1.6*inch)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(1*inch, height - 1.9*inch, "DELIVERY TO:")
    p.setFont("Helvetica", 10)
    p.drawString(1*inch, height - 2.1*inch, f"{order.address.full_name}")
    p.drawString(1*inch, height - 2.25*inch, f"{order.address.address_line_1}")
    p.drawString(1*inch, height - 2.4*inch, f"{order.address.city}, {order.address.state} - {order.address.pincode}")

    # --- Table Header ---
    y = height - 3.2*inch
    p.setFillColor(colors.hexColor("#f8fafc"))
    p.rect(1*inch, y - 5, width - 2*inch, 20, fill=1, stroke=0)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1.1*inch, y, "Item Description")
    p.drawString(3.5*inch, y, "Qty")
    p.drawString(4.2*inch, y, "Price")
    p.drawRightString(width - 1.1*inch, y, "Total")

    # --- Items ---
    y -= 25
    p.setFont("Helvetica", 10)
    for item in order.orderitem_set.all():
        p.drawString(1.1*inch, y, f"{item.product.name[:35]}")
        p.drawString(3.5*inch, y, f"{item.quantity}")
        p.drawString(4.2*inch, y, f"Rs.{item.price}")
        p.drawRightString(width - 1.1*inch, y, f"Rs.{item.get_total()}")
        y -= 20
        if y < 1*inch: # Simple page break check
            p.showPage()
            y = height - 1*inch

    # --- Summary ---
    y -= 20
    p.line(4*inch, y, width - 1*inch, y)
    y -= 20
    p.drawString(4.2*inch, y, "Subtotal:")
    p.drawRightString(width - 1.1*inch, y, f"Rs.{order.subtotal}")
    y -= 15
    p.drawString(4.2*inch, y, "Delivery:")
    p.drawRightString(width - 1.1*inch, y, f"Rs.{order.shipping_cost}")
    y -= 25
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.hexColor("#00b359"))
    p.drawString(4.2*inch, y, "Total Paid:")
    p.drawRightString(width - 1.1*inch, y, f"Rs.{order.total}")

    # --- Footer ---
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.gray)
    p.drawCentredString(width/2, 0.5*inch, "Thank you for shopping with GramaCart - Empowering Rural Delivery.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"GramaCart_Invoice_{order.order_number}.pdf")
    

# from django.shortcuts import render
# from django.core.paginator import Paginator
# from django.db.models import Q, Sum, F, DecimalField
# from django.db.models.functions import Coalesce

# from inventory.models import Inventory
# from admin_dashboard.models import Category
# from .forms import StockLogForm


# def live_inventory(request):

#     query = request.GET.get('q', '').strip()
#     category_id = request.GET.get('category')

#     # =====================================================
#     # BASE INVENTORY QUERY
#     # =====================================================

#     inventories = (
#         Inventory.objects
#         .select_related(
#             'variant',
#             'variant__product',
#             'shop'
#         )
#         .order_by('-updated_at')
#     )

#     # =====================================================
#     # SEARCH
#     # =====================================================

#     if query:
#         inventories = inventories.filter(
#             Q(variant__product__name__icontains=query) |
#             Q(variant__product__description__icontains=query) |
#             Q(shop__name__icontains=query) |
#             Q(variant__unit__icontains=query)
#         )

#     # =====================================================
#     # CATEGORY FILTER
#     # =====================================================

#     if category_id:
#         inventories = inventories.filter(
#             variant__product__category_id=category_id
#         )

#     # =====================================================
#     # INVENTORY STATS
#     # =====================================================

#     inventory_stats = inventories.aggregate(

#         total_inventory_value=Coalesce(
#             Sum(
#                 F('stock') * F('cost_price'),
#                 output_field=DecimalField()
#             ),
#             0
#         ),

#         out_of_stock_count=Coalesce(
#             Sum(
#                 models.Case(
#                     models.When(stock__lte=0, then=1),
#                     default=0,
#                     output_field=models.IntegerField()
#                 )
#             ),
#             0
#         ),

#         low_stock_count=Coalesce(
#             Sum(
#                 models.Case(
#                     models.When(
#                         stock__gt=0,
#                         stock__lte=F('min_stock_level'),
#                         then=1
#                     ),
#                     default=0,
#                     output_field=models.IntegerField()
#                 )
#             ),
#             0
#         )
#     )

#     # =====================================================
#     # PAGINATION
#     # =====================================================

#     paginator = Paginator(inventories, 10)

#     page_number = request.GET.get('page')

#     inventory_page = paginator.get_page(page_number)

#     # =====================================================
#     # CONTEXT
#     # =====================================================

#     context = {

#         "inventories": inventory_page,

#         "categories": Category.objects.all(),

#         "stock_form": StockLogForm(),

#         "query": query,
#         "selected_category": category_id,

#         # Stats
#         "total_inventory_value":
#             inventory_stats['total_inventory_value'],

#         "out_of_stock_count":
#             inventory_stats['out_of_stock_count'],

#         "low_stock_count":
#             inventory_stats['low_stock_count'],
#     }

#     return render(
#         request,
#         "Product/live_inventory.html",
#         context
#     )


from django.db.models import F

def restock_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Create form but we'll handle the logic carefully
        form = StockLogForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Get the adjustment amount (e.g., -20 for expired milk)
                    log = form.save(commit=False)
                    adjustment = log.change_amount 
                    
                    # 2. SAFETY CHECK: Don't allow stock to go below zero
                    # If current is 20 and admin enters -25, set it to 0 instead of -5
                    current_stock = product.stock_available
                    if (current_stock + adjustment) < 0:
                        # Optional: Force it to exactly 0 if they try to subtract too much
                        adjustment = -current_stock 
                        log.change_amount = adjustment
                    
                    # 3. Save the Log Entry
                    log.product = product
                    log.user = request.user # Track WHO made the change
                    log.save()
                    
                    # 4. Update Product Stock using F() expressions for accuracy
                    product.stock_available = F('stock_available') + adjustment
                    product.save()
                    
                    # 5. Refresh to check if it's now 0 to show correct message
                    product.refresh_from_db()
                    status_msg = f"Inventory updated. New balance: {product.stock_available}"
                    if product.stock_available == 0:
                        status_msg += " (Product is now Out of Stock)"
                        
                    messages.success(request, status_msg)
                    
            except Exception as e:
                messages.error(request, f"System Error: {str(e)}")
        else:
            # This is where your "Invalid Data" error was coming from
            # We show exactly what is wrong (e.g., "Must be greater than 0")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Form Error ({field}): {error}")
            
    return redirect('live_inventory')



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from admin_dashboard.models import Product, ProductVariant, Shop
from inventory.models import Inventory


@login_required
def inventory_assign(request):

    products = Product.objects.select_related('category').prefetch_related('variants')
    shops = Shop.objects.select_related('hub')

    inventory_items = Inventory.objects.select_related(
        'variant',
        'variant__product',
        'shop',
        'shop__hub'
    ).order_by('-updated_at')

    if request.method == "POST":

        product_id = request.POST.get("product")
        variant_id = request.POST.get("variant")
        shop_id = request.POST.get("shop")

        stock = int(request.POST.get("stock") or 0)
        cost_price = request.POST.get("cost_price") or 0
        selling_price = request.POST.get("selling_price") or 0
        min_stock_level = request.POST.get("min_stock_level") or 5

        try:
            variant = ProductVariant.objects.get(
                id=variant_id,
                product_id=product_id
            )
            shop = Shop.objects.get(id=shop_id)

            inventory, created = Inventory.objects.get_or_create(
                variant=variant,
                shop=shop,
                defaults={
                    "stock": stock,
                    "cost_price": cost_price,
                    "selling_price": selling_price,
                    "min_stock_level": min_stock_level,
                }
            )

            if not created:
                inventory.stock += stock
                inventory.cost_price = cost_price
                inventory.selling_price = selling_price
                inventory.min_stock_level = min_stock_level
                inventory.save()

            messages.success(request, "Inventory assigned successfully!")
            return redirect("inventory_assign")  # stay on same page

        except Exception as e:
            messages.error(request, str(e))

    return render(request, "inventory/inventory_assign.html", {
        "products": products,
        "shops": shops,
        "inventory_items": inventory_items,  # ✅ THIS IS THE KEY FIX
    })

@login_required
@staff_member_required
def update_min_stock(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        new_level = request.POST.get('min_level')
        
        if new_level is not None:
            product.min_stock_level = int(new_level)
            product.save()
            messages.success(request, f"Alert threshold for {product.name} updated to {new_level}.")
            
    return redirect('live_inventory')


from django.db.models import Count, Sum, Q
from django.utils.timezone import now, timedelta

@staff_member_required
def admin_customer_list(request):
    search_query = request.GET.get('q', '')
    
    # 1. Base Query: Use 'orders' (plural) as suggested by your Choices
    customers = User.objects.filter(is_staff=False).annotate(
        order_count=Count('orders'),             # Changed 'order' to 'orders'
        total_spent=Sum('orders__total')         # Changed 'order__total' to 'orders__total'
    )

    # 2. Search Filter
    if search_query:
        customers = customers.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(orders__address__city__icontains=search_query) # Also 'orders' here
        ).distinct()

    # 3. Dynamic Stats for the Header
    today = now().date()
    seven_days_ago = today - timedelta(days=7)
    
    context = {
        'customers': customers.order_by('-date_joined'),
        'total_customers': User.objects.filter(is_staff=False).count(),
        'total_revenue': customers.aggregate(s=Sum('total_spent'))['s'] or 0,
        'weekly_new': User.objects.filter(is_staff=False, date_joined__gte=seven_days_ago).count(),
    }
    
    return render(request, 'admin_dashboard/customers.html', context)

from django.db.models import Avg

@staff_member_required
def admin_customer_detail(request, user_id):
    customer = get_object_or_404(User, id=user_id)
    customer_orders = customer.orders.all().order_by('-placed_at')
    
    # NEW: Calculate Average Order Value
    avg_order = customer_orders.aggregate(Avg('total'))['total__avg'] or 0
    
    # NEW: Calculate Success Rate
    total_count = customer_orders.count()
    delivered_count = customer_orders.filter(status='delivered').count()
    success_rate = (delivered_count / total_count * 100) if total_count > 0 else 0

    context = {
        'customer': customer,
        'orders': customer_orders,
        'avg_order': avg_order,
        'success_rate': success_rate,
        # ... your previous context ...
    }
    return render(request, 'admin_dashboard/customer_detail.html', context)

#=================================================================
from payments.models import FinancialWallet

def daily_cash_report(request):
    # Get all riders and calculate what they owe GramaCart
    riders = FinancialWallet.objects.filter(user__groups__name='DeliveryBoy')
    
    report = []
    for wallet in riders:
        # Net to collect = (Cash they have) - (The commission we owe them)
        net_to_collect = wallet.cash_in_hand - wallet.pending_balance
        report.append({
            'rider': wallet.user.username,
            'cash_in_hand': wallet.cash_in_hand,
            'our_debt_to_them': wallet.pending_balance,
            'collect_this_amount': net_to_collect,
            'wallet_id': wallet.id
        })
    
    return render(request, 'admin_dashboard/cash_report.html', {'report': report})


from payments.models import FinancialWallet, Payout
from django.db import transaction

@login_required
def rider_cash_settlement_list(request):
    """
    Shows a list of all riders and their current 'Debt' to GramaCart.
    """
    # Only show users in the DeliveryBoy group who have a wallet
    wallets = FinancialWallet.objects.filter(user__groups__name='DeliveryBoy').select_related('user')
    
    for wallet in wallets:
        # Net Cash = (COD collected) - (Earnings we owe them)
        wallet.net_to_collect = wallet.cash_in_hand - wallet.pending_balance
        
    return render(request, 'admin_dashboard/rider_settlement.html', {'wallets': wallets})

@login_required
def settle_rider_handover(request, wallet_id):
    wallet = get_object_or_404(FinancialWallet, id=wallet_id)
    
    if request.method == "POST":
        with transaction.atomic():
            # 1. Create a Payout record for your history/audit
            Payout.objects.create(
                wallet=wallet,
                amount=wallet.pending_balance, # Recording what we paid them
                reference_number=f"CASH_SETTLE_{timezone.now().strftime('%Y%m%d')}"
            )
            
            # 2. Update totals
            wallet.total_withdrawn += wallet.pending_balance
            
            # 3. Reset daily balances to zero
            wallet.pending_balance = 0
            wallet.cash_in_hand = 0
            wallet.save()
            
            messages.success(request, f"Settled account for {wallet.user.username}. Cash received!")
            
    return redirect('rider_cash_settlement_list')


#======================================================


from .models import Shop
from .forms import ShopForm


# =====================================================
# SHOP LIST
# =====================================================

@login_required
def shop_list(request):

    shops = Shop.objects.select_related('hub').order_by('-created_at')

    context = {
        "shops": shops
    }

    return render(request, 'shops/shop_list.html', context)


# =====================================================
# ADD SHOP
# =====================================================

@login_required
def add_shop(request):

    if request.method == 'POST':

        form = ShopForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(request, "Shop created successfully.")

            return redirect('shop_list')

    else:
        form = ShopForm()

    context = {
        "form": form
    }

    return render(request, 'shops/shop_form.html', context)


# =====================================================
# EDIT SHOP
# =====================================================

@login_required
def edit_shop(request, pk):

    shop = get_object_or_404(Shop, pk=pk)

    if request.method == 'POST':

        form = ShopForm(request.POST, instance=shop)

        if form.is_valid():
            form.save()

            messages.success(request, "Shop updated successfully.")

            return redirect('shop_list')

    else:
        form = ShopForm(instance=shop)

    context = {
        "form": form,
        "shop": shop
    }

    return render(request, 'shops/shop_form.html', context)


# =====================================================
# DELETE SHOP
# =====================================================

@login_required
def delete_shop(request, pk):

    shop = get_object_or_404(Shop, pk=pk)

    if request.method == 'POST':

        shop.delete()

        messages.success(request, "Shop deleted successfully.")

        return redirect('shop_list')

    context = {
        "shop": shop
    }

    return render(request, 'shops/shop_confirm_delete.html', context)