from django.shortcuts import render, get_object_or_404,redirect
from django.db.models import Q, Prefetch
from admin_dashboard.models import Product,Category,ProductImage, CompanyInfo
from shop.models import CartItem
from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def get_filtered_products(query=None, category_slug=None):
    """
    Helper function to filter products based on search query or category.
    Prefetches images for better performance.
    """
    products = Product.objects.all().prefetch_related(
        Prefetch('product_images', queryset=ProductImage.objects.all())
    )

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)
        print(f"Filtered by category: {selected_category.name}. Products count: {products.count()}")

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
        print(f"Filtered by query '{query}'. Products count: {products.count()}")

    return products

def get_category_product_map(products):
    """
    Groups products by category for dashboard display.
    """
    category_product_map = defaultdict(list)
    for product in products:
        category_product_map[product.category].append(product)
    return category_product_map


from django.db.models import Avg, Count
from inventory.models import Inventory 

from django.db.models import Q, Prefetch

from admin_dashboard.models import Product


def get_hub_products(query=None, category_slug=None, hub=None):
    """
    Returns PRODUCTS based on INVENTORY availability in a HUB
    """

    # =========================
    # STEP 1: Base inventory filter
    # =========================
    inventory_qs = Inventory.objects.select_related(
        'variant__product',
        'shop__hub',
        'shop'
    ).filter(
        stock__gt=0,
        shop__is_active=True,
    )

    # =========================
    # STEP 2: Hub filter (MOST IMPORTANT)
    # =========================
    if hub:
        inventory_qs = inventory_qs.filter(shop__hub=hub)

    # =========================
    # STEP 3: Category filter
    # =========================
    if category_slug:
        inventory_qs = inventory_qs.filter(
            variant__product__category__slug=category_slug
        )

    # =========================
    # STEP 4: Search filter
    # =========================
    if query:
        inventory_qs = inventory_qs.filter(
            Q(variant__product__name__icontains=query) |
            Q(variant__product__description__icontains=query)
        )

    # =========================
    # STEP 5: Extract PRODUCTS
    # (important: DISTINCT products only)
    # =========================
    products = Product.objects.filter(
        id__in=inventory_qs.values_list('variant__product_id', flat=True)
    ).distinct()

    return products

def public_dashboard(request, category_slug=None):
    query = request.GET.get('q', '').strip()
    star_range = range(1, 6)

    company_info = CompanyInfo.objects.first()
    categories = Category.objects.all()

    # ==============================
    # 1. ACTIVE HUB DETECTION
    # ==============================
    active_hub = None

    if request.user.is_authenticated:
        try:
            profile = request.user.customer_profile
            address = profile.addresses.filter(
                is_default=True,
                is_active=True
            ).first()

            if address:
                active_hub = DeliveryHub.objects.filter(
                    is_active=True,
                    city__iexact=address.city
                ).first()

        except Exception:
            active_hub = None

    # ==============================
    # 2. HUB-BASED PRODUCTS (NEW CORE)
    # ==============================
    products = get_hub_products(
        query=query,
        category_slug=category_slug,
        hub=active_hub
    ).annotate(
        avg_rating_value=Avg('ratings__score'),
        rating_count_value=Count('ratings')
    )

    # ==============================
    # 3. CATEGORY VIEW (OPTIONAL)
    # ==============================
    selected_category = None
    category_product_map = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)

    if not (query or category_slug):
        category_product_map = get_category_product_map(products)

    # ==============================
    # 4. CART COUNT
    # ==============================
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()

    # ==============================
    # 5. WISHLIST IDS
    # ==============================
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(
            WishlistItem.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

    # ==============================
    # 6. CONTEXT
    # ==============================
    context = {
        'categories': categories,
        'selected_products': products,
        'category_product_map': category_product_map,
        'company': company_info,
        'cart_count': cart_count,
        'search_query': query,
        'star_range': star_range,
        'wishlist_ids': wishlist_ids,

        # 🔥 IMPORTANT FOR UI
        'active_hub': active_hub,
    }

    return render(request, 'Public_view/dashboard.html', context)

#----------my profile------------------------

from .forms import CustomerProfileForm

@login_required
def manage_profile(request):
    try:
        profile = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request,"Profile updated successfully")
            return redirect('profile_view')  # redirect to profile view
        else:
            messages.error(request,"please Enter correct details.")
    else:
        form = CustomerProfileForm(instance=profile)

    return render(request, 'profile/manage_profile.html', {'form': form})



@login_required
def profile_view(request):
    try:
        profile = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return redirect('manage_profile')

    # ✅ Use CustomerProfile everywhere (IMPORTANT)
    orders_count = Order.objects.filter(user=request.user).count()
    address_count = Address.objects.filter(customer=profile).count()

    # Status logic
    if orders_count == 0:
        status = "New"
    elif orders_count < 10:
        status = "Active"
    elif orders_count < 30:
        status = "Regular"
    else:
        status = "Premium"

    context = {
        'user': request.user,
        'profile': profile,
        'orders_count': orders_count,
        'address_count': address_count,
        'user_status': status
    }

    return render(request, 'profile/profile_view.html', context)
#=================================================================
from decimal import Decimal

from django.http import JsonResponse

from shop.forms import AddressForm
from shop.utils import check_address_within_hub

# ================================
# Reverse Geocode (AJAX)
# ================================
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="hyperlocal_app")

def reverse_geocode(request):
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if not lat or not lon:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)

    try:
        location = geolocator.reverse(f"{lat},{lon}", exactly_one=True, zoom=18)
        data = location.raw.get('address', {})

        # Collect all potential landmarks for the "Chips"
        poi_list = []
        for key in ['amenity', 'tourism', 'historic', 'shop', 'office', 'building', 'attraction']:
            val = data.get(key)
            if val and val not in poi_list:
                poi_list.append(val.replace('_', ' ').title())

        # Primary landmark for the input field
        landmark = next((l for l in poi_list if l), '')

        response = {
            'street': data.get('road', ''),
            'city': data.get('city') or data.get('town') or data.get('village') or '',
            'pincode': data.get('postcode', ''),
            'state': data.get('state', 'Andhra Pradesh'),
            'country': data.get('country', 'India'),
            'landmark': landmark,
            'nearby_pois': poi_list[:5]  # Send top 5 candidates for the UI chips
        }
        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ================================
# Shared Save Logic
# ================================
def save_address_from_form(form, profile, allow_remote, lat, lon, address_instance=None):
    """
    Saves the address after checking hub distance and default flag.
    """
    address = form.save(commit=False)
    address.customer = profile
    address.latitude = Decimal(lat)
    address.longitude = Decimal(lon)

    # Check if deliverable
    hub_check = check_address_within_hub(address, allow_remote=allow_remote)
    if not hub_check.deliverable:
        return None, "Selected location is outside our delivery area."

    address.distance_km = hub_check.distance_km

    # Handle default address
    if address.is_default:
        Address.objects.filter(customer=profile, is_default=True).exclude(
            pk=address_instance.pk if address_instance else None
        ).update(is_default=False)

    address.save()
    return address, None


# ================================
# Create / Update View (Combined Logic)
# ================================
@login_required
def address_form(request, pk=None):
    profile = CustomerProfile.objects.filter(user=request.user).first()
    if not profile:
        return redirect('manage_profile')
    hubs = DeliveryHub.objects.all() # Fetching hubs for the map circles
    address_instance = None

    if pk:
        address_instance = get_object_or_404(Address, pk=pk, customer=profile)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address_instance)
        allow_remote = request.POST.get('remote_delivery') == "on"
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        # Basic coordinate check
        if not lat or not lon:
            messages.error(request, "Please tap the map to pick your house location.")
        else:
            try:
                lat_dec = Decimal(lat)
                lon_dec = Decimal(lon)
                
                if form.is_valid():
                    # Pass lat/lon directly to the save logic
                    address, error = save_address_from_form(form, profile, allow_remote, lat_dec, lon_dec, address_instance)
                    if error:
                        messages.error(request, error)
                    else:
                        msg = "Address updated!" if pk else "Address saved!"
                        messages.success(request, msg)
                        return redirect('address_list')
            except Exception as e:
                messages.error(request, "Invalid map coordinates.")
    else:
        form = AddressForm(instance=address_instance)

    return render(request, 'address/address_form.html', {
        'form': form,
        'nearest_hubs': hubs, # Crucial for the Leaflet circles
        'address': address_instance
    })

# ================================
# Delete Address
# ================================
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .models import Order, Address,CustomerProfile

@login_required
def address_delete(request, pk):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    address = get_object_or_404(Address, pk=pk, customer=profile)

    if request.method == 'POST':
        # 1. CHECK FOR ACTIVE ORDERS
        # We don't want to hide an address if a Rider is currently looking for it!
        active_orders = Order.objects.filter(
            address=address, 
            status__in=['pending', 'processing', 'shipped']
        ).exists()

        if active_orders:
            messages.error(request, "Cannot remove this address while an order is being delivered to it.")
            return redirect('address_list')

        # 2. SOFT DELETE (Deactivate instead of .delete())
        address.is_active = False
        address.save()
        
        messages.success(request, "Address removed from your profile.")
        return redirect('address_list')

    return render(request, 'address/address_confirm_delete.html', {'address': address})

# ================================
# List Addresses
# ================================
@login_required
def address_list(request):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    
    # 1. FILTER: Only show addresses where is_active is True
    # We order by '-is_default' so their primary address shows at the top
    addresses = Address.objects.filter(
        customer=profile, 
        is_active=True
    ).order_by('-is_default', '-id')
    
    # 2. HUB LOGIC: Keep your delivery hubs for the map/distance features
    hubs = DeliveryHub.objects.filter(is_active=True) # Assuming hubs also have an active status
    
    return render(request, 'address/address_list.html', {
        'addresses': addresses,
        'nearest_hubs': hubs
    })

#--------------------------------------------------------------------



from .models import CartItem, WishlistItem
from django.utils import timezone


# -------------------------
# 🛒 CART VIEWS
# -------------------------


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from shop.models import CartItem
from admin_dashboard.models import Product

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Get current cart count
    cart_count = CartItem.objects.filter(user=request.user).count()

    # Return JSON for fetch
    return JsonResponse({
        'success': True,
        'product_name': product.name,
        'cart_count': cart_count
    })





# -------------------------
# 💚 WISHLIST VIEWS
# -------------------------


from .models import WishlistItem, Product

@login_required
def wishlist_view(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    """
    Toggle product in wishlist. If it's already there, remove it.
    Returns JSON response for AJAX.
    """
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            # already exists → remove it (toggle)
            wishlist_item.delete()
            return JsonResponse({'status': 'removed', 'message': f"{product.name} removed from wishlist."})
        
        return JsonResponse({'status': 'added', 'message': f"{product.name} added to wishlist."})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(WishlistItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, "Item removed from wishlist.")
    return redirect('wishlist_view')

#=============================================================

from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal

# Import your optimized utilities
from shop.utils import calculate_shipping_cost

from .models import Product, Order, OrderItem, Address
from payments.models import PaymentMethod
from payments.models import Payment

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    user = request.user
    
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    
    # --- FIX ISSUE #2 & #3: Stock Validation for GET (Preview) ---
    if product.stock_available < quantity:
        messages.warning(request, f"Sorry, only {product.stock_available} units left in stock.")
        # If stock is 0, they shouldn't even be here, redirect them back
        if product.stock_available == 0:
            return redirect('public_dashboard')

    user_addresses = Address.objects.filter(customer__user=user)
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order')

    if request.method == "GET":
        subtotal = product.price * quantity
        default_address = user_addresses.first()
        shipping_fee = Decimal('0')
        shipping_fee = Decimal('0')
        is_serviceable = True

        if default_address:
            ship_res = calculate_shipping_cost(default_address)

            raw_fee = ship_res.get("customer_fee")
            is_serviceable = not ship_res.get("error") and raw_fee is not None

            if is_serviceable:
                shipping_fee = Decimal(str(raw_fee))
            else:
                shipping_fee = Decimal('0')

        totals = {
            'sub_total': subtotal,
            'shipping_cost': shipping_fee,
            'final_total': subtotal + shipping_fee
        }

        return render(request, 'shop/checkout.html', {
            'product': product,
            'quantity': quantity,
            'user_addresses': user_addresses,
            'payment_methods': payment_methods,
            'order_totals': totals,
            'is_serviceable': is_serviceable,
        })

    # ---------------- POST (Processing the Instant Buy) ----------------
    address_id = request.POST.get('address_id')
    payment_method_id = request.POST.get('payment_method')

    if not address_id or not payment_method_id:
        messages.error(request, "Please select an address and payment method.")
        return redirect('buy_now', product_id=product.id)

    selected_address = get_object_or_404(Address, customer__user=user, id=address_id)
    payment_method = get_object_or_404(PaymentMethod, id=payment_method_id, is_active=True)

    shipping_res = calculate_shipping_cost(selected_address)

    raw_fee = shipping_res.get("customer_fee")
    is_serviceable = not shipping_res.get("error") and raw_fee is not None

    if not is_serviceable:
        messages.error(
            request,
            "Sorry, we are not delivering to this address. Please select another address."
        )
        return redirect('buy_now', product_id=product.id)

    customer_fee = Decimal(str(raw_fee))
    subtotal = product.price * quantity
    final_total = subtotal + customer_fee

    try:
        with transaction.atomic():
            # --- FIX ISSUE #2: Final Stock Check before creating Order ---
            # select_for_update() locks the row so two people can't buy the same item at once
            fresh_product = Product.objects.select_for_update().get(id=product.id)
            
            if fresh_product.stock_available < quantity:
                messages.error(request, f"Could not complete order. Only {fresh_product.stock_available} units left.")
                return redirect('public_dashboard')

            # --- FIX: Subtract Stock ---
            fresh_product.stock_available -= quantity
            fresh_product.save()

            # 2. Create Order
            order = Order.objects.create(
                user=user,
                address=selected_address,
                subtotal=subtotal,
                shipping_cost=customer_fee,
                total=final_total,
                status='pending'
            )

            # 3. Create single OrderItem
            OrderItem.objects.create(
                order=order,
                product=fresh_product,
                quantity=quantity,
                price=fresh_product.price
            )

            # 4. Create Payment
            Payment.objects.create(
                order=order,
                method=payment_method,
                amount=final_total,
                currency='INR',
                status='pending'
            )

            # 5. TRIGGER LOGISTICS ENGINE
            from delivery_portal.models import Delivery 
            Delivery.objects.create(
                order=order,
                status='pending' # It stays pending until Admin clicks 'Pack'
            )

    except Exception as e:
        print(f"Buy Now Error: {str(e)}")
        messages.error(request, "Order failed. Please try again.")
        return redirect('buy_now', product_id=product.id)

    # 6. Success Routing
    if payment_method.name.lower() == 'cod':
        messages.success(request, "Order placed! We are fetching your items now.")
        return redirect('order_detail', order_id=order.id)

    return redirect('payment', order_id=order.id)

@login_required
def get_buy_now_shipping_cost(request, product_id):
    user = request.user
    address_id = request.GET.get("address_id")
    
    if not address_id:
        return JsonResponse({"success": False, "error": "Address not provided"}, status=400)

    try:
        address = Address.objects.get(customer__user=user, id=address_id)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Address not found"}, status=404)

    # 1. Get the shipping info from your utility
    shipping_info = calculate_shipping_cost(address)

    # 2. STRICT VALIDATION:
    # An area is ONLY serviceable if the utility didn't error 
    # AND the database actually returned a fee (even if the fee is 0.00).
    # If customer_fee is None, it means no Shipping Slab exists for that distance.
    raw_fee = shipping_info.get("customer_fee")
    is_serviceable = not shipping_info.get('error') and raw_fee is not None

    if not is_serviceable:
        return JsonResponse({
            "success": False,
            "message": "Sorry currently we are not serving this area .Please select another address.",
            "shipping_cost": 0,
            "distance": float(shipping_info.get("distance_km") or 0)
        })

    # 3. AREA IS VALID - Return full data
    return JsonResponse({
        "success": True,
        "shipping_cost": float(raw_fee),
        "rider_earning": float(shipping_info.get("rider_earning") or 0),
        "platform_fee": float(shipping_info.get("platform_fee") or 0),
        "distance": float(shipping_info.get("distance_km") or 0),
        "hub": shipping_info.get("hub_name", "Unknown")
    })
#=================================

from django.shortcuts import get_object_or_404
from shop.models import Rating, WishlistItem  # 👈 add Wishlist

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    average_rating = product.avg_rating
    reviews = product.ratings.select_related('user').order_by('-created_at')

    user_rating = None
    if request.user.is_authenticated:
        user_rating = reviews.filter(user=request.user).first()

    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:6]

    # ✅ 🔥 ADD THIS BLOCK
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = WishlistItem.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)

    context = {
        'product': product,
        'related_products': related_products,
        'star_range': range(1, 6),
        'average_rating': average_rating,
        'reviews': reviews,
        'user_rating': user_rating,
        'rating_count': product.rating_count,

        # ✅ 👇 IMPORTANT
        'wishlist_ids': list(wishlist_ids),
    }

    return render(request, 'Public_view/product_detail.html', context)

from django.views.decorators.http import require_POST
# =================== CART VIEW ===================
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import CartItem, Product

def get_cart_totals(user):
    cart_items = CartItem.objects.filter(user=user)
    # Change 'get_effective_price()' to 'price'
    sub_total = sum(float(item.product.price) * item.quantity for item in cart_items)
    
    
       
    return {
        'sub_total': sub_total,
        
        
        'cart_count': cart_items.count()
    }

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return render(request, 'shop/cart.html', {'cart_items': cart_items, 'order_totals': None})
    
    order_totals = get_cart_totals(request.user)
    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'order_totals': order_totals
    })

@login_required
@require_POST
def update_cart_quantity(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
        data = json.loads(request.body)
        new_quantity = int(data.get('quantity', 1))

        if new_quantity < 1:
            return JsonResponse({'success': False, 'message': 'Minimum 1 item required'})

        cart_item.quantity = new_quantity
        cart_item.save()

        totals = get_cart_totals(request.user)
        
        # Change 'get_effective_price()' to 'price' here too!
        item_total = float(cart_item.product.price) * cart_item.quantity

        return JsonResponse({
            'success': True,
            'item_total': item_total,
            'sub_total': totals['sub_total'],
            'cart_count': totals['cart_count']
        })
    except (CartItem.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'message': 'Update failed'})

@login_required
@require_POST
def remove_from_cart(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id, user=request.user)
        cart_item.delete()
        
        totals = get_cart_totals(request.user)
        
        return JsonResponse({
            'success': True,
            'cart_empty': totals['cart_count'] == 0,
            'sub_total': totals['sub_total'],
            'cart_count': totals['cart_count']
        })
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})
    
#==========================================================
from .utils import calculate_order_totals, calculate_shipping_cost, check_address_within_hub
from admin_dashboard.utils import haversine

from admin_dashboard.models import DeliveryHub

from django.conf import settings
import requests


# ===== LocationIQ helper =====
def get_lat_long_from_address(address_text):
    """
    Fetch latitude and longitude from LocationIQ API using address string.
    Returns tuple: (latitude, longitude) or (None, None) if failed.
    """
    url = "https://us1.locationiq.com/v1/search.php"
    params = {
        "key": settings.LOCATIONIQ_ACCESS_TOKEN,
        "q": address_text,
        "format": "json",
        "limit": 1
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    except Exception as e:
        print(f"LocationIQ Error: {e}")
    return None, None

from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal

# Import your new optimized utilities
from shop.utils import calculate_shipping_cost, calculate_order_totals

from .models import CartItem, Order, OrderItem, Address
from payments.models import PaymentMethod
from payments.models import Payment

@login_required
def cart_checkout(request):
    user = request.user
    # 1. Fetch cart items with a lock on the products to prevent stock changes during calculation
    cart_items = CartItem.objects.filter(user=user).select_related('product')

    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect('cart_view')

    user_addresses = Address.objects.filter(customer__user=user)
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order')

    if request.method == "GET":
        
        totals = calculate_order_totals(cart_items, address=None)
        
        return render(request, 'shop/checkout_cart.html', {
            'cart_items': cart_items,
            'user_addresses': user_addresses,
            'payment_methods': payment_methods,
            'order_totals': totals,
        })

    # ---------------- POST Processing ----------------
    address_id = request.POST.get('address_id')
    payment_method_id = request.POST.get('payment_method')

    if not address_id or not payment_method_id:
        messages.error(request, "Please select both an address and a payment method.")
        return redirect('cart_checkout')

    selected_address = get_object_or_404(Address, customer__user=user, id=address_id)
    payment_method = get_object_or_404(PaymentMethod, id=payment_method_id, is_active=True)
    totals = calculate_order_totals(cart_items, address=selected_address)

    try:
        with transaction.atomic():
            # 2. STOCK VALIDATION LOOP (The "Guard")
            # We must check every single product in the cart before creating the order
            for item in cart_items:
                # select_for_update() prevents other users from buying these items right now
                product = Product.objects.select_for_update().get(id=item.product.id)
                
                if product.stock_available < item.quantity:
                    messages.error(request, f"Insufficient stock for {product.name}. Only {product.stock_available} left.")
                    return redirect('cart_view') # Send them back to adjust their quantity
                
                # 3. DEDUCT STOCK
                product.stock_available -= item.quantity
                product.save()

            # 4. Create the Order
            order = Order.objects.create(
                user=user,
                address=selected_address,
                subtotal=totals['sub_total'],
                shipping_cost=totals['shipping_cost'],
                tax=totals['taxes'],
                total=totals['final_total'],
                status='pending'
            )

            # 5. Create Order Items
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                ) for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            # 6. Create Payment Record
            Payment.objects.create(
                order=order,
                method=payment_method,
                amount=totals['final_total'],
                currency='INR',
                status='pending'
            )

            # 7. Clear the Cart and Trigger Logistics
            cart_items.delete()
            from delivery_portal.models import Delivery
            Delivery.objects.create(
                order=order,
                status='pending' # It stays pending until Admin clicks 'Pack'
            )

    except Exception as e:
        print(f"Checkout Error: {str(e)}") 
        messages.error(request, "There was a problem processing your order. Please try again.")
        return redirect('cart_checkout')

    # SUCCESS ROUTING
    if payment_method.name.lower() == 'cod':
        messages.success(request, f"Order #{order.id} placed! A rider is being assigned.")
        return redirect('order_detail', order_id=order.id)

    return redirect('payment', order_id=order.id)

# ---------------- AJAX: Get Shipping Cost ----------------

from shop.models import Address

"""
@login_required
def get_shipping_cost(request):
    user = request.user
    address_id = request.GET.get("address_id")
    if not address_id:
        return JsonResponse({"error": "Address not provided"}, status=400)

    try:
        address = Address.objects.get(customer__user=user, id=address_id)
    except Address.DoesNotExist:
        return JsonResponse({"error": "Address not found"}, status=404)

    # Get cart items
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    # Calculate shipping cost
    shipping_info = calculate_shipping_cost(address)
    shipping_cost = Decimal(shipping_info.get("customer_fee", 0))

    # Calculate new order totals
    order_totals = calculate_order_totals(cart_items, address)

    return JsonResponse({
        "shipping_cost": float(shipping_cost),
        "sub_total": float(order_totals["sub_total"]),
        "taxes": float(order_totals["taxes"]),
        "final_total": float(order_totals["final_total"])
    })
"""

@login_required
def get_shipping_cost(request):
    user = request.user
    address_id = request.GET.get("address_id")

    if not address_id:
        return JsonResponse({"success": False, "error": "Address not provided"}, status=400)

    try:
        address = Address.objects.get(customer__user=user, id=address_id)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Address not found"}, status=404)

    # Get cart items
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items.exists():
        return JsonResponse({"success": False, "error": "Cart is empty"}, status=400)

    # 🔥 SAME LOGIC AS BUY NOW
    shipping_info = calculate_shipping_cost(address)

    raw_fee = shipping_info.get("customer_fee")
    is_serviceable = not shipping_info.get("error") and raw_fee is not None

    if not is_serviceable:
        return JsonResponse({
            "success": False,
            "message": "Sorry currently we are not serving this area. Please select another address.",
            "shipping_cost": 0,
            "distance": float(shipping_info.get("distance_km") or 0)
        })

    # ✅ VALID AREA → continue calculations
    order_totals = calculate_order_totals(cart_items, address)

    return JsonResponse({
        "success": True,
        "shipping_cost": float(raw_fee),
        "sub_total": float(order_totals["sub_total"]),
        "taxes": float(order_totals["taxes"]),
        "final_total": float(order_totals["final_total"]),
        "distance": float(shipping_info.get("distance_km") or 0),
        "hub": shipping_info.get("hub_name", "Unknown")
    })
#===========================================================
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-placed_at')  # Assuming the user is authenticated
    order_items = OrderItem.objects.all()
    return render(request, 'shop/order_list.html', {'orders': orders,'order_items': order_items,})

#==================================================================

# from .models import OrderItem  

# def order_detail(request, order_id):
#     order = get_object_or_404(Order, id=order_id, user=request.user)
#     order_items = OrderItem.objects.filter(order=order)
#     return render(request, 'order/order_detail.html', {
#         'order': order,
#         'order_items': order_items,
#     })

from django.shortcuts import get_object_or_404, render
from .models import Order, OrderItem,Rating

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    # products already reviewed by this user
    rated_products = Rating.objects.filter(
        user=request.user,
        product__in=[item.product for item in order_items]
    ).values_list('product_id', flat=True)

    return render(request, 'order/order_detail.html', {
        'order': order,
        'order_items': order_items,
        'rated_products': list(rated_products),
    })

#=========================================================

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Logic: If it reached this view, the database has the order.
    # We show a "Success" message even if status is 'pending' (for COD).
    
    return render(request, 'order_confirmation.html', {
        'order': order,
        'message': "Your order has been placed successfully!",
        'next_step': "The village hub is now reviewing your items."
    })

from .forms import RatingForm

@login_required
def rate_product(request, id):
    product = get_object_or_404(Product, id=id)

    # 🔥 STEP 1: check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status='delivered'
    ).exists()

    if not has_purchased:
        return HttpResponse("You can only rate after purchase delivery.")

    # 🔥 STEP 2: existing rating
    user_rating = Rating.objects.filter(
        product=product,
        user=request.user
    ).first()

    # 🔥 STEP 3: form handling
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=user_rating)

        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.product = product
            rating.save()

            return redirect('product_detail', slug=product.slug)
    else:
        form = RatingForm(instance=user_rating)

    return render(request, 'shop/rate_product.html', {
        'form': form,
        'product': product,
        'user_rating': user_rating
    })

from .models import Order

# VIEW 1: Renders the actual Tracking Page
@login_required
def track_order(request, order_id):
    # Security: Ensure only the customer who placed the order can track it
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/track_order.html', {'order': order})


# VIEW 2: Sends the Live JSON data (Lat/Lng) to the Javascript
@login_required
def get_order_status_json(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Safely get the delivery object and the rider's profile
    delivery = getattr(order, 'delivery', None)
    rider_name = None
    rider_phone = None

    if delivery and delivery.delivery_boy:
        rider_name = delivery.delivery_boy.get_full_name() or delivery.delivery_boy.username
        # Assuming you have a phone field on your DeliveryProfile
        profile = getattr(delivery.delivery_boy, 'delivery_profile', None)
        rider_phone = profile.phone_number if profile else None

    customer_friendly_status = {
        'pending': 'Finding a Delivery Partner...',
        'assigned': 'Rider Assigned', # New status for GramaCart
        'out_for_delivery': 'Rider is on the way!',
        'delivered': 'Arrived at your location',
    }

    return JsonResponse({
        'status_display': customer_friendly_status.get(order.status, order.get_status_display()),
        'status_raw': order.status,
        
        # Rider Info
        'rider_name': rider_name,
        'rider_phone': rider_phone,
        
        # GPS Data
        'rider_lat': float(delivery.current_lat) if delivery and delivery.current_lat else None,
        'rider_lng': float(delivery.current_lng) if delivery and delivery.current_lng else None,
        
        # Home Destination
        'home_lat': float(order.address.latitude) if order.address.latitude else None,
        'home_lng': float(order.address.longitude) if order.address.longitude else None,
    })