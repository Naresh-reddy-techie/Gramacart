from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.urls import reverse
from django.db.models import (
    Q,
    Avg,
    Count,
    Prefetch,
)

from admin_dashboard.models import (
    Product,
    ProductVariant,
    Category,
    ProductImage,
    CompanyInfo,
    DeliveryHub,
)

from inventory.models import Inventory

from shop.models import (
    CartItem,
    WishlistItem,
)

from shop.services.product_catalog import get_hub_products

# =========================================================
# PUBLIC DASHBOARD
# =========================================================

from admin_dashboard.models import Banner
from django.db.models import Q

def public_dashboard(request, category_slug=None):

    # -----------------------------------------------------
    # SEARCH QUERY
    # -----------------------------------------------------

    query = request.GET.get("q", "").strip()

    # -----------------------------------------------------
    # COMPANY
    # -----------------------------------------------------

    company = CompanyInfo.objects.first()

    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    categories = Category.objects.only(
        "id",
        "name",
        "slug"
    )

    # -----------------------------------------------------
    # ACTIVE HUB
    # -----------------------------------------------------

    active_hub_id = request.session.get(
        "active_hub_id"
    )

    active_hub = DeliveryHub.objects.filter(
        id=active_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).only(
        "id",
        "name"
    ).first()
    

    # -----------------------------------------------------
    # HUB REQUIRED
    # -----------------------------------------------------

    if not active_hub:
        return redirect("where_we_deliver")

    

    all_banners = Banner.objects.filter(
        is_active=True,
        page__in=['shop', 'all']
    ).filter(
        Q(hub=active_hub) | Q(hub__isnull=True)
    ).select_related('hub')

    banners = [banner for banner in all_banners if banner.is_live()]

    # -----------------------------------------------------
    # SELECTED CATEGORY
    # -----------------------------------------------------

    selected_category = None

    if category_slug:

        selected_category = get_object_or_404(
            Category.objects.only(
                "id",
                "name",
                "slug"
            ),
            slug=category_slug
        )

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    products = get_hub_products(
        hub=active_hub,
        query=query,
        category_slug=category_slug
    )

    # IMPORTANT:
    # DO NOT REMOVE OUT OF STOCK PRODUCTS
    # They should still appear as
    # "Coming Soon"

    # -----------------------------------------------------
    # CART COUNT
    # -----------------------------------------------------

    cart_count = 0

    if request.user.is_authenticated:

        cart_count = CartItem.objects.filter(
            user=request.user
        ).count()

    # -----------------------------------------------------
    # WISHLIST IDS
    # -----------------------------------------------------

    wishlist_ids = []

    if request.user.is_authenticated:

        wishlist_ids = list(

            WishlistItem.objects.filter(
                user=request.user
            ).values_list(
                "product_id",
                flat=True
            )

        )

    # -----------------------------------------------------
    # CATALOG VERSION
    # -----------------------------------------------------

    latest_inventory = (
        Inventory.objects
        .order_by("-updated_at")
        .first()
    )

    catalog_version = (
        int(latest_inventory.updated_at.timestamp())
        if latest_inventory
        else 0
    )

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {

        "company": company,

        "categories": categories,

        "selected_category": selected_category,

        "products": products,

        "search_query": query,

        "cart_count": cart_count,

        "wishlist_ids": wishlist_ids,

        "active_hub": active_hub,

        "delivery_ready": True,

        "star_range": range(1, 6),

        "catalog_version": catalog_version,

        'banners': banners,

    }

    return render(
        request,
        "Public_view/dashboard.html",
        context
    )


#=============================================

from django.http import JsonResponse
from inventory.models import Inventory


def catalog_version(request):

    latest_inventory = (
        Inventory.objects
        .order_by("-updated_at")
        .first()
    )

    version = (
        int(latest_inventory.updated_at.timestamp())
        if latest_inventory
        else 0
    )

    return JsonResponse({
        "catalog_version": version
    })

# =========================================================
# WHERE SHOULD WE DELIVER
# =========================================================

from django.shortcuts import render

from admin_dashboard.models import DeliveryHub


def where_should_we_deliver(request):

    """
    Public delivery hub selection page.

    Responsibilities:
    - Show active delivery hubs
    - Support remote/manual selection
    - Used before entering marketplace
    """

    hubs_queryset = (

        DeliveryHub.objects

        .filter(
            is_active=True,
            is_accepting_orders=True
        )

        .order_by(
            "state",
            "district",
            "mandal",
            "village"
        )

        .values(
            "id",
            "name",
            "state",
            "district",
            "mandal",
            "village"
        )
    )

    hubs = []

    for hub in hubs_queryset:

        hubs.append({

            "id": hub["id"],

            "name": (
                hub["name"] or ""
            ).strip(),

            "state": (
                hub["state"] or ""
            ).strip(),

            "district": (
                hub["district"] or ""
            ).strip(),

            "mandal": (
                hub["mandal"] or ""
            ).strip(),

            "village": (
                hub["village"] or ""
            ).strip(),
        })

    return render(
        request,
        "shop/where_we_deliver.html",
        {
            "hubs": hubs
        }
    )

# =========================================================
# DELIVERY AVAILABILITY CHECK
# =========================================================

import json
import logging

from decimal import Decimal
from types import SimpleNamespace

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from admin_dashboard.models import DeliveryHub

from shop.utils import check_address_within_hub

logger = logging.getLogger(__name__)


@require_POST
@csrf_protect
def check_delivery_availability(request):

    """
    Production-ready delivery availability engine.

    Supports:
    - GPS/local delivery
    - Remote/manual hub selection
    - Session-based hub locking
    """

    try:

        # =====================================================
        # REQUEST DATA
        # =====================================================

        data = json.loads(request.body or "{}")

        flow_type = data.get("type")

        if flow_type not in ["local", "remote"]:

            return JsonResponse({
                "success": False,
                "message": "Invalid delivery type."
            })

        active_hub = None
        hub_check = None

        delivery_latitude = None
        delivery_longitude = None

        # =====================================================
        # LOCAL DELIVERY
        # =====================================================

        if flow_type == "local":

            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if latitude is None or longitude is None:

                return JsonResponse({
                    "success": False,
                    "message": "Unable to detect your location."
                })

            temp_address = SimpleNamespace(
                latitude=Decimal(str(latitude)),
                longitude=Decimal(str(longitude))
            )

            hub_check = check_address_within_hub(
                temp_address,
                allow_remote=False
            )

            # =================================================
            # NO HUB FOUND
            # =================================================

            if not hub_check.delivery_hub:

                return JsonResponse({
                    "success": False,
                    "message": "No nearby delivery hubs found."
                })

            # =================================================
            # OUTSIDE DELIVERY RADIUS
            # =================================================

            if not hub_check.deliverable:

                return JsonResponse({
                    "success": True,
                    "deliverable": False,
                    "message": "Sorry, we are not serving this area yet.",
                    "hub_name": hub_check.delivery_hub.name,
                    "distance_km": round(float(hub_check.distance_km or 0),2),
                    "delivery_radius_km": float(hub_check.delivery_hub.max_delivery_radius_km),
                })

            active_hub = hub_check.delivery_hub

            delivery_latitude = float(latitude)
            delivery_longitude = float(longitude)

        # =====================================================
        # REMOTE DELIVERY
        # =====================================================

        else:

            hub_id = data.get("hub_id")

            if not hub_id:

                return JsonResponse({
                    "success": False,
                    "message": "Please select delivery hub."
                })

            active_hub = DeliveryHub.objects.filter(
                id=hub_id,
                is_active=True,
                is_accepting_orders=True
            ).first()

            if not active_hub:

                return JsonResponse({
                    "success": False,
                    "message": "Selected delivery hub unavailable."
                })

            delivery_latitude = float(active_hub.latitude)
            delivery_longitude = float(active_hub.longitude)

        # =====================================================
        # STORE SESSION
        # =====================================================

        request.session["active_hub_id"] = active_hub.id

        request.session["delivery_type"] = flow_type

        request.session["delivery_latitude"] = delivery_latitude

        request.session["delivery_longitude"] = delivery_longitude

        # =====================================================
        # REMOTE SESSION DATA
        # =====================================================

        if flow_type == "remote":

            request.session["selected_state"] = active_hub.state

            request.session["selected_district"] = active_hub.district

            request.session["selected_mandal"] = active_hub.mandal

            request.session["selected_village"] = active_hub.village

        else:

            request.session.pop("selected_state", None)

            request.session.pop("selected_district", None)

            request.session.pop("selected_mandal", None)

            request.session.pop("selected_village", None)

        # =====================================================
        # SUCCESS RESPONSE
        # =====================================================

        return JsonResponse({

            "success": True,

            "deliverable": True,

            "message": "Delivery available in your area.",

            "hub_name": active_hub.name,

            "hub_location": (
                active_hub.landmark
                or active_hub.full_address
                or active_hub.village
            ),

            "distance_km": (
                round(float(hub_check.distance_km), 2)
                if hub_check else 0
            ),

            "redirect_url": "/shop/public_dashboard/"
        })

    # =========================================================
    # INVALID JSON
    # =========================================================

    except json.JSONDecodeError:

        return JsonResponse({
            "success": False,
            "message": "Invalid request format."
        })

    # =========================================================
    # SERVER ERROR
    # =========================================================

    except Exception as e:

        logger.exception(
            f"Delivery availability check failed: {e}"
        )

        return JsonResponse({
            "success": False,
            "message": "Something went wrong. Please try again."
        })


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

    # =====================================================
    # PROFILE
    # =====================================================

    profile = get_object_or_404(
        CustomerProfile.objects.select_related("user"),
        user=request.user
    )

    # =====================================================
    # ADDRESSES
    # =====================================================

    addresses_qs = Address.active.filter(
        customer=profile
    )

    address_count = addresses_qs.count()

    # =====================================================
    # DEFAULT ADDRESS
    # =====================================================

    default_address = addresses_qs.filter(
        is_default=True
    ).first()

    # fallback
    if not default_address:
        default_address = addresses_qs.first()

    # =====================================================
    # ORDERS
    # =====================================================

    orders_qs = Order.objects.filter(
        user=request.user
    )

    orders_count = orders_qs.count()

    # =====================================================
    # USER STATUS ENGINE
    # =====================================================

    if orders_count == 0:
        user_status = "New"

    elif orders_count < 10:
        user_status = "Active"

    elif orders_count < 30:
        user_status = "Regular"

    else:
        user_status = "Premium"

    # =====================================================
    # WISHLIST
    # =====================================================

    wishlist_count = 0

    if hasattr(profile, "wishlist_items"):
        wishlist_count = profile.wishlist_items.count()

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "profile": profile,

        "orders_count": orders_count,

        "address_count": address_count,

        "wishlist_count": wishlist_count,

        "user_status": user_status,

        "default_address": default_address,
    }

    return render(
        request,
        "profile/profile_view.html",
        context
    )
# =========================================================
# ACTIVE HUBS JSON
# =========================================================

def get_active_hubs_json():

    hubs = DeliveryHub.objects.filter(
        is_active=True,
        is_accepting_orders=True
    ).only(
        "id",
        "name",
        "latitude",
        "longitude",
        "max_delivery_radius_km"
    )

    return json.dumps([

        {
            "id": hub.id,
            "name": hub.name,
            "lat": float(hub.latitude),
            "lon": float(hub.longitude),
            "radius": float(
                hub.max_delivery_radius_km or 7
            ) * 1000
        }

        for hub in hubs
    ])


# =========================================================
# REVERSE GEOCODE
# =========================================================

def reverse_geocode(request):

    lat = request.GET.get("lat")
    lon = request.GET.get("lon")

    if not lat or not lon:

        return JsonResponse({
            "success": False,
            "message": "Coordinates missing."
        })

    try:

        lat = float(lat)
        lon = float(lon)

        location = geolocator.reverse(
            (lat, lon),
            exactly_one=True
        )

        if not location:

            return JsonResponse({
                "success": False,
                "message": "Location not found."
            })

        data = location.raw.get(
            "address",
            {}
        )

        city = (
            data.get("city")
            or data.get("town")
            or data.get("village")
            or ""
        )

        return JsonResponse({

            "success": True,

            "street": data.get("road", ""),

            "city": city,

            "state": data.get("state", ""),

            "country": data.get(
                "country",
                "India"
            ),

            "pincode": data.get(
                "postcode",
                ""
            ),

            "landmark": (
                data.get("amenity")
                or data.get("shop")
                or data.get("building")
                or ""
            ),
        })

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Unable to fetch location."
        })

# =========================================================
# ADDRESS CREATE / UPDATE (PRODUCTION GRADE)
# =========================================================

import json
import logging

from geopy.distance import geodesic

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)

from admin_dashboard.models import DeliveryHub

from shop.forms import AddressForm

from .models import (
    Address,
    CustomerProfile
)

logger = logging.getLogger(__name__)


# =========================================================
# ADDRESS FORM
# =========================================================

@login_required
def address_form(request, pk=None):

    logger.info("========== ADDRESS FORM START ==========")

    # =====================================================
    # CUSTOMER
    # =====================================================

    profile = get_object_or_404(
        CustomerProfile,
        user=request.user
    )

    # =====================================================
    # EDIT MODE
    # =====================================================

    address_instance = None

    if pk:

        address_instance = get_object_or_404(
            Address.active,
            pk=pk,
            customer=profile
        )

        logger.info(
            "EDIT ADDRESS ID=%s",
            address_instance.id
        )

    # =====================================================
    # FORM
    # =====================================================

    form = AddressForm(
        request.POST or None,
        instance=address_instance
    )

    # =====================================================
    # ACTIVE HUBS
    # =====================================================

    hubs_qs = DeliveryHub.objects.filter(
        is_active=True,
        is_accepting_orders=True
    ).only(
        "id",
        "name",
        "latitude",
        "longitude",
        "max_delivery_radius_km"
    )

    # =====================================================
    # USER LOCATION
    # =====================================================

    user_lat = None
    user_lon = None

    # ---------------------------------------------
    # POST GPS
    # ---------------------------------------------

    if request.method == "POST":

        try:

            user_lat = float(
                request.POST.get("latitude")
            )

            user_lon = float(
                request.POST.get("longitude")
            )

            logger.info(
                "GPS FROM POST => %s,%s",
                user_lat,
                user_lon
            )

        except Exception:

            logger.warning(
                "POST GPS INVALID"
            )

    # ---------------------------------------------
    # SESSION GPS
    # ---------------------------------------------

    if user_lat is None or user_lon is None:

        try:

            session_lat = request.session.get(
                "delivery_latitude"
            )

            session_lon = request.session.get(
                "delivery_longitude"
            )

            if session_lat and session_lon:

                user_lat = float(session_lat)
                user_lon = float(session_lon)

                logger.info(
                    "GPS FROM SESSION => %s,%s",
                    user_lat,
                    user_lon
                )

        except Exception:

            logger.warning(
                "SESSION GPS INVALID"
            )

    # =====================================================
    # ACTIVE HUB RESOLUTION
    # =====================================================

    active_hub = None

    # ---------------------------------------------
    # GPS BASED HUB
    # ---------------------------------------------

    if user_lat and user_lon and hubs_qs.exists():

        try:

            active_hub = min(

                hubs_qs,

                key=lambda hub: geodesic(

                    (
                        float(user_lat),
                        float(user_lon)
                    ),

                    (
                        float(hub.latitude),
                        float(hub.longitude)
                    )

                ).km
            )

            logger.info(
                "GPS HUB => %s",
                active_hub.name
            )

        except Exception as e:

            logger.error(
                "GPS HUB ERROR => %s",
                str(e)
            )

    # ---------------------------------------------
    # SESSION HUB
    # ---------------------------------------------

    if not active_hub:

        session_hub_id = request.session.get(
            "active_hub_id"
        )

        if session_hub_id:

            active_hub = hubs_qs.filter(
                id=session_hub_id
            ).first()

            logger.info(
                "SESSION HUB => %s",
                active_hub.name if active_hub else None
            )

    # ---------------------------------------------
    # FINAL FALLBACK
    # ---------------------------------------------

    if not active_hub:

        active_hub = hubs_qs.first()

        logger.info(
            "FALLBACK HUB => %s",
            active_hub.name if active_hub else None
        )

    # =====================================================
    # SESSION SYNC
    # =====================================================

    if active_hub:

        request.session["active_hub_id"] = (
            active_hub.id
        )

        logger.info(
            "SESSION HUB SAVED => %s",
            active_hub.name
        )

    # ---------------------------------------------
    # SAVE CUSTOMER GPS (NOT HUB GPS)
    # ---------------------------------------------

    if user_lat and user_lon:

        request.session["delivery_latitude"] = (
            float(user_lat)
        )

        request.session["delivery_longitude"] = (
            float(user_lon)
        )

        logger.info(
            "SESSION GPS SAVED => %s,%s",
            user_lat,
            user_lon
        )

    # =====================================================
    # SAVE FORM
    # =====================================================

    if request.method == "POST":

        logger.info("POST REQUEST RECEIVED")

        if form.is_valid():

            address = form.save(
                commit=False
            )

            address.customer = profile

            # -----------------------------------------
            # SINGLE DEFAULT ADDRESS
            # -----------------------------------------

            if address.is_default:

                Address.active.filter(
                    customer=profile,
                    is_default=True
                ).exclude(
                    pk=address.pk
                ).update(
                    is_default=False
                )

            # -----------------------------------------
            # SAVE
            # -----------------------------------------

            address.save()

            logger.info(
                "ADDRESS SAVED => ID=%s",
                address.id
            )

            messages.success(
                request,
                "Address saved successfully."
            )

            next_page = request.POST.get("next") or request.GET.get("next")

            if next_page in [None, "", "None", "null", "undefined"]:
                next_page = None

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect("address_list")

        logger.error(
            "FORM ERRORS => %s",
            form.errors
        )

        messages.error(
            request,
            "Please correct form errors."
        )

    # =====================================================
    # HUB JSON
    # =====================================================

    delivery_hubs_json = json.dumps([

        {
            "id": hub.id,

            "name": hub.name,

            "lat": float(hub.latitude),

            "lon": float(hub.longitude),

            "radius": float(
                hub.max_delivery_radius_km or 7
            ) * 1000
        }

        for hub in hubs_qs

    ])

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "form": form,

        "address": address_instance,

        "delivery_hubs_json": delivery_hubs_json,

        "active_hub": {

            "id": active_hub.id,

            "name": active_hub.name,

            "lat": float(active_hub.latitude),

            "lon": float(active_hub.longitude)

        } if active_hub else None
    }

    logger.info(
        "FINAL ACTIVE HUB => %s",
        active_hub.name if active_hub else None
    )

    logger.info("========== ADDRESS FORM END ==========")

    return render(
        request,
        "address/address_form.html",
        context
    )

# =========================================================
# ADDRESS LIST
# =========================================================
@login_required
def address_list(request):

    profile = get_object_or_404(
        CustomerProfile,
        user=request.user
    )

    addresses = (
        Address.active
        .filter(customer=profile)
        .order_by("-is_default", "-created_at")
    )

    delivery_hubs = (
        DeliveryHub.objects
        .filter(
            is_active=True,
            is_accepting_orders=True
        )
        .only(
            "id",
            "name",
            "latitude",
            "longitude",
            "max_delivery_radius_km"
        )
    )

    context = {

        "addresses": addresses,

        "delivery_hubs_json": [

            {
                "id": hub.id,
                "name": hub.name,
                "lat": float(hub.latitude),
                "lon": float(hub.longitude),
                "radius": float(
                    hub.max_delivery_radius_km or 7
                ) * 1000
            }

            for hub in delivery_hubs
        ]
    }

    return render(
        request,
        "address/address_list.html",
        context
    )

# =========================================================
# ADDRESS DELETE
# =========================================================

@login_required
def address_delete(request, pk):

    profile = get_object_or_404(
        CustomerProfile,
        user=request.user
    )

    address = get_object_or_404(
        Address.active,
        pk=pk,
        customer=profile
    )

    if request.method != "POST":

        return redirect(
            "address_list"
        )

    # =====================================================
    # ACTIVE ORDERS CHECK
    # =====================================================

    active_orders = Order.objects.filter(
        address=address,
        status__in=[
            "pending",
            "confirmed",
            "packed",
            "assigned",
            "out_for_delivery"
        ]
    ).exists()

    if active_orders:

        messages.error(
            request,
            "Cannot delete address with active orders."
        )

        return redirect(
            "address_list"
        )

    # =====================================================
    # PREVENT DELETING LAST ADDRESS
    # =====================================================

    remaining = Address.active.filter(
        customer=profile
    ).count()

    if remaining <= 1:

        messages.error(
            request,
            "At least one address required."
        )

        return redirect(
            "address_list"
        )

    # =====================================================
    # SOFT DELETE
    # =====================================================

    address.deactivate()

    messages.success(
        request,
        "Address removed successfully."
    )

    return redirect(
        "address_list"
    )
#--------------------------------------------------------------------



from .models import CartItem, WishlistItem
from django.utils import timezone


# -------------------------
# 🛒 CART VIEWS
# -------------------------
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect
)

from admin_dashboard.models import (
    Product,
    ProductVariant,
    DeliveryHub
)

from inventory.models import Inventory

from .models import CartItem


# =========================================================
# ADD TO CART
# =========================================================
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect
)

from admin_dashboard.models import (
    Product,
    ProductVariant,
    DeliveryHub
)

from inventory.models import Inventory

from .models import CartItem


# =========================================================
# ADD TO CART
# =========================================================
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect
)
from django.views.decorators.http import require_POST

from admin_dashboard.models import (
    DeliveryHub,
    Product,
    ProductVariant
)

from inventory.models import Inventory

from shop.models import CartItem


# =========================================================
# HELPER
# =========================================================

def _fail(
    request,
    message,
    redirect_url="cart_view",
    redirect_kwargs=None
):

    redirect_kwargs = redirect_kwargs or {}

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        return JsonResponse({
            "success": False,
            "message": message
        })

    messages.error(request, message)

    return redirect(
        redirect_url,
        **redirect_kwargs
    )


# =========================================================
# ADD TO CART (PRODUCTION READY)
# =========================================================

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect
)
from django.views.decorators.http import require_POST

from admin_dashboard.models import (
    DeliveryHub,
    Product,
    ProductVariant
)

from inventory.models import Inventory

from .models import CartItem


logger = logging.getLogger(__name__)


# =========================================================
# STANDARD ERROR RESPONSE
# =========================================================

def _fail(
    request,
    message,
    redirect_url="cart_view",
    redirect_kwargs=None,
    status=400,
    extra_data=None
):

    redirect_kwargs = redirect_kwargs or {}
    extra_data = extra_data or {}

    # =====================================================
    # AJAX RESPONSE
    # =====================================================

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        response_data = {
            "success": False,
            "message": message
        }

        response_data.update(extra_data)

        return JsonResponse(
            response_data,
            status=status
        )

    # =====================================================
    # NORMAL REQUEST
    # =====================================================

    messages.error(request, message)

    return redirect(
        redirect_url,
        **redirect_kwargs
    )


# =========================================================
# ADD TO CART
# =========================================================

@login_required
@require_POST
def add_to_cart(request, product_id):

    user = request.user

    # =====================================================
    # PRODUCT
    # =====================================================

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    # =====================================================
    # SAFE REQUEST PARSING
    # =====================================================

    data = {}

    if request.body:

        try:
            data = json.loads(request.body)
        except Exception:
            data = {}

    variant_id = (
        request.POST.get("variant_id")
        or data.get("variant_id")
        or request.GET.get("variant_id")
    )

    if not variant_id:

        return _fail(
            request,
            "Please select product variant."
        )

    try:

        quantity = int(
            request.POST.get("quantity")
            or data.get("quantity", 1)
        )

    except (TypeError, ValueError):

        quantity = 1

    quantity = max(1, quantity)

    # =====================================================
    # VARIANT
    # =====================================================

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product=product,
        is_active=True
    )

    # =====================================================
    # ACTIVE HUB (SOURCE OF TRUTH)
    # =====================================================

    session_hub_id = request.session.get(
        "active_hub_id"
    )

    if not session_hub_id:

        return _fail(
            request,
            "Please select delivery location first.",
            redirect_url="where_we_deliver"
        )

    active_hub = DeliveryHub.objects.filter(
        id=session_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    if not active_hub:

        return _fail(
            request,
            "Selected delivery hub unavailable.",
            redirect_url="where_we_deliver"
        )

    # =====================================================
    # TRANSACTION
    # =====================================================

    try:

        with transaction.atomic():

            # =================================================
            # CLEAN CROSS HUB CART ITEMS
            # =================================================

            CartItem.objects.filter(
                user=user
            ).exclude(
                hub=active_hub
            ).delete()

            # =================================================
            # INVENTORY (STRICT HUB ISOLATION)
            # =================================================

            inventory = (
                Inventory.objects
                .select_for_update()
                .select_related(
                    "shop",
                    "shop__hub",
                    "variant"
                )
                .filter(
                    variant=variant,
                    stock__gt=0,
                    shop__is_active=True,
                    shop__hub=active_hub
                )
                .order_by(
                    "selling_price",
                    "-updated_at"
                )
                .first()
            )

            if not inventory:

                return _fail(
                    request,
                    "Product unavailable in selected delivery area."
                )

            # =================================================
            # SECURITY VALIDATION
            # =================================================

            if inventory.shop.hub_id != active_hub.id:

                logger.warning(
                    "Hub mismatch detected. "
                    f"Inventory={inventory.id}, "
                    f"Hub={active_hub.id}"
                )

                return _fail(
                    request,
                    "Inventory validation failed."
                )

            # =================================================
            # ALLOWED QUANTITY
            # =================================================

            allowed_quantity = min(
                inventory.stock,
                inventory.max_order_quantity
            )

            if quantity > allowed_quantity:

                return _fail(
                    request,
                    f"You can order maximum "
                    f"{allowed_quantity} item(s)."
                )

            # =================================================
            # EXISTING CART ITEM
            # =================================================

            cart_item = (
                CartItem.objects
                .select_for_update()
                .filter(
                    user=user,
                    variant=variant,
                    hub=active_hub
                )
                .first()
            )

            # =================================================
            # UPDATE EXISTING CART
            # =================================================

            if cart_item:

                new_quantity = (
                    cart_item.quantity + quantity
                )

                if new_quantity > allowed_quantity:

                    return _fail(
                        request,
                        f"You can order maximum "
                        f"{allowed_quantity} item(s)."
                    )

                cart_item.quantity = new_quantity

            # =================================================
            # CREATE CART ITEM
            # =================================================

            else:

                cart_item = CartItem(
                    user=user,
                    product=product,
                    variant=variant,
                    inventory=inventory,
                    hub=active_hub,
                    quantity=quantity
                )

            # =================================================
            # ALWAYS SYNC PRICE + INVENTORY
            # =================================================

            cart_item.inventory = inventory

            cart_item.unit_price = (
                inventory.selling_price
            )

            cart_item.save()

            # =================================================
            # CART COUNT
            # =================================================

            cart_count = CartItem.objects.filter(
                user=user,
                hub=active_hub
            ).count()

    except Exception as e:

        logger.exception(
            f"ADD TO CART ERROR: {str(e)}"
        )

        return _fail(
            request,
            "Failed to add product to cart."
        )

    # =====================================================
    # AJAX RESPONSE
    # =====================================================

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        return JsonResponse({

            "success": True,

            "message": "Added to cart.",

            "cart_count": cart_count,

            "hub_id": active_hub.id,

            "hub_name": active_hub.name,

            "product": product.name,

            "variant": getattr(
                variant,
                "display_name",
                ""
            ),

            "quantity": quantity
        })

    # =====================================================
    # NORMAL RESPONSE
    # =====================================================

    messages.success(
        request,
        "Added to cart successfully."
    )

    return redirect("cart_view")
# =========================================================
# STANDARD ERROR RESPONSE HELPER
# =========================================================

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect


def _fail(
    request,
    message,
    redirect_url="cart_view",
    redirect_kwargs=None,
    status=400,
    extra_data=None
):
    """
    Production-ready unified error handler.

    Supports:
    - AJAX requests
    - Normal requests
    - Future API scalability
    - Standardized responses
    """

    redirect_kwargs = redirect_kwargs or {}
    extra_data = extra_data or {}

    # =====================================================
    # AJAX / API RESPONSE
    # =====================================================

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        response_data = {
            "success": False,
            "message": message
        }

        response_data.update(extra_data)

        return JsonResponse(
            response_data,
            status=status
        )

    # =====================================================
    # DJANGO MESSAGE FRAMEWORK
    # =====================================================

    messages.error(request, message)

    # =====================================================
    # STANDARD REDIRECT
    # =====================================================

    return redirect(
        redirect_url,
        **redirect_kwargs
    )
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

from payments.models import Payment
# =========================================================
# BUY NOW CHECKOUT
# =========================================================

def safe_redirect(next_page, fallback):
    if next_page and next_page.startswith("/"):
        return redirect(next_page)
    return redirect(fallback)

@login_required
def buy_now(request, product_id):

    user = request.user
    next_page = request.GET.get("next") or request.POST.get("next")

    if not next_page or next_page in ["None", "null", "undefined"]:
        next_page = request.get_full_path() # 🔥 fallback to BUY NOW page itself

    # =====================================================
    # ACTIVE HUB (SESSION SOURCE OF TRUTH)
    # =====================================================

    session_hub_id = request.session.get(
        "active_hub_id"
    )

    if not session_hub_id:

        messages.error(
            request,
            "Please select delivery location first."
        )

        return redirect(
            "where_we_deliver"
        )

    active_hub = DeliveryHub.objects.filter(
        id=session_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    if not active_hub:

        messages.error(
            request,
            "Selected delivery hub unavailable."
        )

        return redirect(
            "where_we_deliver"
        )

    # =====================================================
    # PRODUCT
    # =====================================================

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    # =====================================================
    # VARIANT
    # =====================================================

    variant_id = (
        request.POST.get("variant_id")
        or request.GET.get("variant_id")
    )

    if not variant_id:

        messages.error(
            request,
            "Please select product variant."
        )

        return redirect(
            "product_detail",
            slug=product.slug
        )

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product=product,
        is_active=True
    )

    # =====================================================
    # QUANTITY
    # =====================================================

    try:

        quantity = int(
            request.POST.get("quantity")
            or request.GET.get("quantity")
            or 1
        )

    except (TypeError, ValueError):

        quantity = 1

    quantity = max(1, quantity)

    # =====================================================
    # INVENTORY (STRICT HUB ISOLATION)
    # =====================================================

    inventory = (
        Inventory.objects
        .select_related(
            "shop",
            "shop__hub",
            "variant"
        )
        .filter(
            variant=variant,
            stock__gt=0,
            shop__is_active=True,
            shop__hub=active_hub
        )
        .order_by(
            "selling_price",
            "-updated_at"
        )
        .first()
    )

    if not inventory:

        messages.error(
            request,
            "Product unavailable in selected delivery area."
        )

        return redirect(
            "product_detail",
            slug=product.slug
        )

    # =====================================================
    # HUB SECURITY CHECK
    # =====================================================

    if inventory.shop.hub_id != active_hub.id:

        messages.error(
            request,
            "Inventory hub mismatch detected."
        )

        return redirect(
            "product_detail",
            slug=product.slug
        )

    # =====================================================
    # STOCK VALIDATION
    # =====================================================

    if quantity > inventory.stock:

        messages.error(
            request,
            f"Only {inventory.stock} item(s) available."
        )

        return redirect(
            "product_detail",
            slug=product.slug
        )

    # =====================================================
    # MAX ORDER LIMIT
    # =====================================================

    if quantity > inventory.max_order_quantity:

        messages.error(
            request,
            f"Maximum {inventory.max_order_quantity} item(s) allowed."
        )

        return redirect(
            "product_detail",
            slug=product.slug
        )

    # =====================================================
    # USER ADDRESSES
    # =====================================================

    user_addresses = Address.objects.filter(
        customer__user=user,
        is_active=True
    ).order_by(
        "-is_default",
        "-id"
    )

    # =====================================================
    # PAYMENT METHODS
    # =====================================================

    payment_methods = PaymentMethod.objects.filter(
        is_active=True
    ).order_by(
        "sort_order"
    )

    # =====================================================
    # PRICING
    # =====================================================

    unit_price = Decimal(
        str(inventory.selling_price)
    )

    sub_total = (
        unit_price * quantity
    )

    order_totals = {
        "sub_total": sub_total,
        "shipping_cost": Decimal("0.00"),
        "final_total": sub_total
    }

    # =====================================================
    # GET REQUEST
    # =====================================================

    if request.method == "GET":

        return render(
            request,
            "shop/checkout.html",
            {
                "product": product,
                "variant": variant,
                "inventory": inventory,
                "quantity": quantity,
                "user_addresses": user_addresses,
                "payment_methods": payment_methods,
                "active_hub": active_hub,
                "order_totals": order_totals,
                "next": next_page, 
            }
        )

    # =====================================================
    # SAVE BUY NOW SESSION
    # =====================================================

    request.session["buy_now_checkout"] = {
        "product_id": product.id,
        "variant_id": variant.id,
        "quantity": quantity,
        "hub_id": active_hub.id,
    }

    request.session.modified = True
    
    # =====================================================
    # ADDRESS
    # =====================================================

    address_id = request.POST.get(
        "address_id"
    )

    payment_method_id = request.POST.get(
        "payment_method"
    )

    if not address_id or not payment_method_id:

        messages.error(
            request,
            "Please select address and payment method."
        )
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        return redirect(
            "buy_now",
            product_id=product.id
        )

    address = get_object_or_404(
        Address,
        id=address_id,
        customer__user=user,
        is_active=True
    )

    payment_method = get_object_or_404(
        PaymentMethod,
        id=payment_method_id,
        is_active=True
    )

    # =====================================================
    # SHIPPING + GEO VALIDATION
    # =====================================================

    shipping_data = calculate_shipping_cost(
        address=address,
        delivery_hub=active_hub
    )

    if shipping_data.get("error"):

        messages.error(
            request,
            shipping_data.get(
                "message",
                "Delivery unavailable"
            )
        )

        return redirect(
            "buy_now",
            product_id=product.id
        )

    shipping_cost = Decimal(
        str(
            shipping_data.get(
                "customer_fee",
                0
            )
        )
    )

    final_total = (
        sub_total + shipping_cost
    )

    # =====================================================
    # ORDER CREATION
    # =====================================================

    try:

        with transaction.atomic():

            locked_inventory = (
                Inventory.objects
                .select_for_update()
                .select_related(
                    "shop",
                    "shop__hub"
                )
                .get(
                    id=inventory.id
                )
            )

            # =============================================
            # FINAL STOCK CHECK
            # =============================================

            if locked_inventory.stock < quantity:

                raise Exception(
                    f"Only {locked_inventory.stock} item(s) available."
                )

            # =============================================
            # FINAL HUB VALIDATION
            # =============================================

            if locked_inventory.shop.hub_id != active_hub.id:

                raise Exception(
                    "Inventory hub mismatch."
                )

            # =============================================
            # REDUCE STOCK
            # =============================================

            locked_inventory.reduce_stock(
                quantity
            )

            # =============================================
            # CREATE ORDER
            # =============================================

            order = Order.objects.create(

                user=user,

                address=address,

                shop=locked_inventory.shop,

                hub=active_hub,

                subtotal=sub_total,

                shipping_cost=shipping_cost,

                total=final_total,

                status="pending"
            )

            # =============================================
            # ORDER ITEM
            # =============================================

            OrderItem.objects.create(

                order=order,

                product=product,

                variant=variant,

                inventory=locked_inventory,

                quantity=quantity,

                price=unit_price,

                variant_name=getattr(
                    variant,
                    "display_name",
                    ""
                )
            )

            # =============================================
            # PAYMENT
            # =============================================

            Payment.objects.create(

                order=order,

                method=payment_method,

                amount=final_total,

                currency="INR",

                status="pending"
            )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

        return redirect(
            "buy_now",
            product_id=product.id
        )

    # =====================================================
    # COD FLOW
    # =====================================================

    if payment_method.name.lower() == "cod":

        messages.success(
            request,
            "Order placed successfully."
        )

        return redirect(
            "order_detail",
            order_id=order.id
        )

    # =====================================================
    # ONLINE PAYMENT
    # =====================================================

    return redirect(
        "payment",
        order_id=order.id
    )

# =========================================================
# AJAX SHIPPING CALCULATOR
# =========================================================

@login_required
def get_buy_now_shipping_cost(
    request,
    product_id
):

    user = request.user

    # =====================================================
    # ACTIVE HUB
    # =====================================================

    session_hub_id = request.session.get(
        "active_hub_id"
    )

    if not session_hub_id:

        return JsonResponse({
            "success": False,
            "message": "Delivery location not selected"
        })

    active_hub = DeliveryHub.objects.filter(
        id=session_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    if not active_hub:

        return JsonResponse({
            "success": False,
            "message": "Delivery hub unavailable"
        })

    # =====================================================
    # ADDRESS
    # =====================================================

    address_id = request.GET.get(
        "address_id"
    )

    if not address_id:

        return JsonResponse({
            "success": False,
            "message": "Address required"
        })

    try:

        address = Address.objects.get(
            id=address_id,
            customer__user=user,
            is_active=True
        )

    except Address.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": "Invalid address"
        })

    # =====================================================
    # SHIPPING ENGINE
    # =====================================================

    shipping_data = calculate_shipping_cost(
        address=address,
        delivery_hub=active_hub
    )

    if shipping_data.get("error"):

        return JsonResponse({
            "success": False,
            "message": shipping_data.get(
                "message",
                "Delivery unavailable"
            )
        })

    return JsonResponse({

        "success": True,

        "shipping_cost": float(
            shipping_data.get(
                "customer_fee",
                0
            )
        ),

        "rider_earning": float(
            shipping_data.get(
                "rider_earning",
                0
            )
        ),

        "platform_fee": float(
            shipping_data.get(
                "platform_fee",
                0
            )
        ),

        "distance": float(
            shipping_data.get(
                "distance_km",
                0
            )
        ),

        "hub": shipping_data.get(
            "hub_name",
            active_hub.name
        )
    })
#=================================
from decimal import Decimal

from django.db.models import Prefetch
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from decimal import Decimal

from django.db.models import Prefetch
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from admin_dashboard.models import (
    Product,
    ProductVariant,
    DeliveryHub,
)

from inventory.models import Inventory
from shop.models import WishlistItem

from shop.services.product_catalog import get_similar_products

def product_detail(request, slug):

    # =====================================================
    # ACTIVE HUB
    # =====================================================
    active_hub_id = request.session.get(
        "active_hub_id"
    )

    active_hub = DeliveryHub.objects.filter(
        id=active_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    # =====================================================
    # NO ACTIVE HUB
    # =====================================================
    if not active_hub:

        return redirect(
            "where_we_deliver"
        )

    # =====================================================
    # INVENTORY QUERY
    # =====================================================
    inventory_qs = Inventory.objects.select_related(
        "shop",
        "shop__hub",
        "variant"
    ).filter(

        variant__is_active=True,

        shop__is_active=True,

        shop__hub=active_hub,

        selling_price__isnull=False

    )

    # =====================================================
    # PRODUCT QUERY
    # =====================================================
    product = get_object_or_404(

        Product.objects.prefetch_related(

            "product_images",

            Prefetch(

                "variants",

                queryset=ProductVariant.objects.filter(
                    is_active=True
                ).prefetch_related(

                    Prefetch(
                        "inventory_items",
                        queryset=inventory_qs,
                        to_attr="hub_inventory"
                    )

                ),

                to_attr="active_variants"

            )

        ),

        slug=slug,
        is_active=True

    )

    # =====================================================
    # VARIANTS
    # =====================================================
    variants = []

    for variant in product.active_variants:

        # -------------------------------------------------
        # SAFETY
        # -------------------------------------------------
        if not variant.is_active:
            continue

        inventories = getattr(
            variant,
            "hub_inventory",
            []
        )

        # -------------------------------------------------
        # NO INVENTORY
        #
        # Product exists globally
        # but inventory not assigned yet
        # -------------------------------------------------
        if not inventories:
            continue

        # -------------------------------------------------
        # VALID PRICES
        # -------------------------------------------------
        valid_prices = [

            Decimal(str(inv.selling_price))

            for inv in inventories

            if inv.selling_price is not None

        ]

        if not valid_prices:
            continue

        # -------------------------------------------------
        # LOWEST PRICE
        # -------------------------------------------------
        min_price = min(valid_prices)

        # -------------------------------------------------
        # TOTAL STOCK
        # -------------------------------------------------
        total_stock = sum(

            int(inv.stock or 0)

            for inv in inventories

        )

        # -------------------------------------------------
        # STOCK STATUS
        # -------------------------------------------------
        in_stock = total_stock > 0

        if total_stock <= 0:

            stock_status = "Coming Soon"

        elif total_stock <= 5:

            stock_status = f"Only {total_stock} left"

        else:

            stock_status = "In Stock"

        # -------------------------------------------------
        # APPEND
        # -------------------------------------------------
        variants.append({

            "id": variant.id,

            "name": variant.display_name,

            "price": min_price,

            "stock": total_stock,

            "in_stock": in_stock,

            "status": stock_status,

        })

    # =====================================================
    # SORT VARIANTS
    #
    # PRIORITY:
    # 1. In-stock first
    # 2. Lower price first
    # =====================================================
    variants.sort(

        key=lambda x: (

            not x["in_stock"],

            x["price"]

        )

    )

    # =====================================================
    # PRODUCT STOCK STATUS
    # =====================================================
    is_in_stock = any(

        variant["in_stock"]

        for variant in variants

    )

    # =====================================================
    # DEFAULT VARIANT
    # =====================================================
    default_variant = next(

        (

            variant

            for variant in variants

            if variant["in_stock"]

        ),

        variants[0] if variants else None

    )

    # =====================================================
    # REVIEWS
    # =====================================================
    reviews = product.ratings.select_related(
        "user"
    ).order_by(
        "-created_at"
    )

    # =====================================================
    # WISHLIST
    # =====================================================
    wishlist_ids = []

    if request.user.is_authenticated:

        wishlist_ids = list(

            WishlistItem.objects.filter(
                user=request.user
            ).values_list(
                "product_id",
                flat=True
            )

        )

    # =====================================================
    # RELATED PRODUCTS
    # =====================================================
    related_products = get_similar_products(
        product=product,
        hub=active_hub,
        limit=8,
    )
    # =====================================================
    # CONTEXT
    # =====================================================
    context = {

        # PRODUCT
        "product": product,

        # VARIANTS
        "variants": variants,

        # DEFAULT VARIANT
        "default_variant": default_variant,

        # STOCK
        "is_in_stock": is_in_stock,

        # REVIEWS
        "reviews": reviews,

        "avg_rating": product.avg_rating,

        "rating_count": product.rating_count,

        # WISHLIST
        "wishlist_ids": wishlist_ids,

        # HUB
        "active_hub": active_hub,

        # RELATED PRODUCTS
        "similar_products": related_products,

    }

    # =====================================================
    # RENDER
    # =====================================================
    return render(

        request,

        "Public_view/product_detail.html",

        context

    )

 

from django.views.decorators.http import require_POST
# =================== CART VIEW ===================
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from admin_dashboard.models import DeliveryHub

from inventory.models import Inventory

from .models import CartItem



def get_cart_totals(user, request):

    active_hub_id = request.session.get("active_hub_id")

    if not active_hub_id:
        return {
            "sub_total": Decimal("0.00"),
            "shipping_cost": Decimal("0.00"),
            "final_total": Decimal("0.00"),
            "cart_count": 0
        }

    cart_items = CartItem.objects.select_related(
        "product",
        "variant"
    ).filter(user=user)

    sub_total = Decimal("0.00")

    for item in cart_items:

        inventory = Inventory.objects.select_related(
            "shop",
            "shop__hub"
        ).filter(
            variant=item.variant,
            stock__gt=0,
            selling_price__isnull=False,
            shop__is_active=True,
            shop__hub_id=active_hub_id
        ).order_by("selling_price").first()

        if not inventory:
            continue

        item_price = Decimal(str(inventory.selling_price))
        item_total = item_price * item.quantity
        sub_total += item_total

    shipping_cost = Decimal("0.00")  # adjust later if needed
    final_total = sub_total + shipping_cost

    return {
        "sub_total": sub_total,
        "shipping_cost": shipping_cost,
        "final_total": final_total,
        "cart_count": cart_items.count()
    }

# =========================================================
# CART PAGE
# =========================================================

@login_required
def cart_view(request):

    user = request.user

    # =====================================================
    # ACTIVE HUB
    # =====================================================

    active_hub_id = request.session.get(
        "active_hub_id"
    )

    active_hub = DeliveryHub.objects.filter(
        id=active_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).only(
        "id",
        "name"
    ).first()

    # =====================================================
    # NO HUB
    # =====================================================

    if not active_hub:

        messages.error(
            request,
            "Please select delivery location."
        )

        return redirect(
            "where_we_deliver"
        )

    # =====================================================
    # CART ITEMS
    # =====================================================

    cart_items = CartItem.objects.select_related(
        "product",
        "variant",
        "inventory",
        "inventory__shop",
        "inventory__shop__hub"
    ).prefetch_related(
        "product__product_images"
    ).filter(
        user=user,
        hub=active_hub
    ).order_by(
        "-added_on"
    )

    enriched_items = []

    # =====================================================
    # PROCESS ITEMS
    # =====================================================

    for item in cart_items:

        item.unavailable = False
        item.out_of_stock = False
        item.price_changed = False

        item.unavailable_reason = ""

        inventory = item.inventory

        # -------------------------------------------------
        # INVENTORY MISSING
        # -------------------------------------------------

        if not inventory:

            item.unavailable = True
            item.unavailable_reason = (
                "Inventory unavailable"
            )

            enriched_items.append(item)

            continue

        # -------------------------------------------------
        # HUB SECURITY
        # -------------------------------------------------

        if inventory.shop.hub_id != active_hub.id:

            item.unavailable = True
            item.unavailable_reason = (
                "Invalid delivery zone"
            )

            enriched_items.append(item)

            continue

        # -------------------------------------------------
        # PRODUCT STATUS
        # -------------------------------------------------

        if not item.product.is_active:

            item.unavailable = True
            item.unavailable_reason = (
                "Product unavailable"
            )

            enriched_items.append(item)

            continue

        # -------------------------------------------------
        # VARIANT STATUS
        # -------------------------------------------------

        if not item.variant.is_active:

            item.unavailable = True
            item.unavailable_reason = (
                "Variant unavailable"
            )

            enriched_items.append(item)

            continue

        # -------------------------------------------------
        # SHOP STATUS
        # -------------------------------------------------

        if not inventory.shop.is_active:

            item.unavailable = True
            item.unavailable_reason = (
                "Shop unavailable"
            )

            enriched_items.append(item)

            continue

        # -------------------------------------------------
        # STOCK CHECK
        # -------------------------------------------------

        if inventory.stock <= 0:

            item.out_of_stock = True

            item.unavailable_reason = (
                "Out of stock"
            )

        # -------------------------------------------------
        # AUTO QUANTITY FIX
        # -------------------------------------------------

        allowed_quantity = min(
            inventory.stock,
            inventory.max_order_quantity
        )

        if allowed_quantity > 0 and item.quantity > allowed_quantity:

            item.quantity = allowed_quantity

            item.save(
                update_fields=["quantity"]
            )

        # -------------------------------------------------
        # PRICE SYNC
        # -------------------------------------------------

        current_price = Decimal(
            str(inventory.selling_price)
        )

        if item.unit_price != current_price:

            item.price_changed = True

            item.unit_price = current_price

            item.save(
                update_fields=["unit_price"]
            )

        # -------------------------------------------------
        # TOTALS
        # -------------------------------------------------

        item.item_total = (
            Decimal(str(item.unit_price))
            * item.quantity
        )

        enriched_items.append(item)

    # =====================================================
    # TOTALS
    # =====================================================

    order_totals = get_cart_totals(
        user,
        request
    )

    # =====================================================
    # CHECKOUT BLOCK
    # =====================================================

    checkout_blocked = any([

        item.unavailable
        or item.out_of_stock

        for item in enriched_items
    ])

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "cart_items": enriched_items,

        "order_totals": order_totals,

        "active_hub": active_hub,

        "checkout_blocked": checkout_blocked,

        "cart_count": cart_items.count(),
    }

    return render(
        request,
        "shop/cart.html",
        context
    )

# =========================================================
# UPDATE CART QUANTITY
# =========================================================

@login_required
@require_POST
def update_cart_quantity(request, cart_item_id):

    user = request.user

    # =====================================================
    # ACTIVE HUB
    # =====================================================

    active_hub_id = request.session.get(
        "active_hub_id"
    )

    if not active_hub_id:

        return JsonResponse({
            "success": False,
            "message": "Delivery location missing"
        })

    # =====================================================
    # CART ITEM
    # =====================================================

    try:

        cart_item = CartItem.objects.select_related(
            "inventory",
            "inventory__shop",
            "inventory__shop__hub",
            "product",
            "variant"
        ).get(
            id=cart_item_id,
            user=user,
            hub_id=active_hub_id
        )

    except CartItem.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": "Cart item not found"
        })

    # =====================================================
    # REQUEST DATA
    # =====================================================

    try:

        data = json.loads(request.body.decode("utf-8"))

        new_quantity = int(
            data.get("quantity", 1)
        )

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Invalid quantity"
        })

    # =====================================================
    # MINIMUM VALIDATION
    # =====================================================

    if new_quantity < 1:

        return JsonResponse({
            "success": False,
            "message": "Minimum quantity is 1"
        })

    # =====================================================
    # INVENTORY
    # =====================================================

    inventory = cart_item.inventory

    if not inventory:

        return JsonResponse({
            "success": False,
            "message": "Inventory unavailable"
        })

    # =====================================================
    # HUB SECURITY
    # =====================================================

    if inventory.shop.hub_id != active_hub_id:

        return JsonResponse({
            "success": False,
            "message": "Hub mismatch detected"
        })

    # =====================================================
    # STOCK VALIDATION
    # =====================================================

    if new_quantity > inventory.stock:

        return JsonResponse({
            "success": False,
            "message": (
                f"Only {inventory.stock} item(s) available"
            )
        })

    # =====================================================
    # MAX ORDER LIMIT
    # =====================================================

    if new_quantity > inventory.max_order_quantity:

        return JsonResponse({
            "success": False,
            "message": (
                f"Maximum {inventory.max_order_quantity} item(s) allowed"
            )
        })

    # =====================================================
    # UPDATE
    # =====================================================

    cart_item.quantity = new_quantity

    cart_item.unit_price = inventory.selling_price

    cart_item.save(
        update_fields=[
            "quantity",
            "unit_price"
        ]
    )

    # =====================================================
    # TOTALS
    # =====================================================

    item_total = (
        Decimal(str(inventory.selling_price))
        * new_quantity
    )

    totals = get_cart_totals(
        user,
        request
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse({

        "success": True,

        "quantity": new_quantity,

        "item_total": float(item_total),

        "sub_total": float(
            totals["sub_total"]
        ),

        "shipping_cost": float(
            totals.get("shipping_cost", 0)
        ),

        "final_total": float(
            totals["final_total"]
        ),

        "cart_count": totals["cart_count"]
    })

# =========================================================
# REMOVE FROM CART
# =========================================================
@login_required
@require_POST
def remove_from_cart(request, item_id):

    try:

        cart_item = CartItem.objects.get(
            id=item_id,
            user=request.user
        )

        cart_item.delete()

        totals = get_cart_totals(
            request.user,
            request
        )

        return JsonResponse({
            "success": True,
            "cart_empty": totals["cart_count"] == 0,
            "sub_total": float(totals["sub_total"]),
            "cart_count": totals["cart_count"]
        })

    except CartItem.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": "Item not found"
        })
#==========================================================


# =========================================================
# LOCATIONIQ GEOCODING
# =========================================================

import logging
import requests

from typing import Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def get_lat_long_from_address(
    address_text: str
) -> Tuple[Optional[float], Optional[float]]:

    """
    Convert address text into latitude & longitude.

    Production-ready features:
    - India-only search
    - Timeout protection
    - Safe JSON parsing
    - Error logging
    - Returns (None, None) safely
    """

    if not address_text:
        return None, None

    url = "https://us1.locationiq.com/v1/search.php"

    params = {
        "key": settings.LOCATIONIQ_ACCESS_TOKEN,
        "q": address_text,
        "format": "json",
        "limit": 1,
        "countrycodes": "in"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        if not data or not isinstance(data, list):
            return None, None

        first_result = data[0]

        latitude = first_result.get("lat")
        longitude = first_result.get("lon")

        if not latitude or not longitude:
            return None, None

        return (
            float(latitude),
            float(longitude)
        )

    except requests.exceptions.Timeout:

        logger.warning(
            "LocationIQ timeout for address: %s",
            address_text
        )

    except requests.exceptions.RequestException as e:

        logger.error(
            "LocationIQ request failed: %s",
            str(e)
        )

    except (ValueError, TypeError, KeyError) as e:

        logger.error(
            "LocationIQ invalid response: %s",
            str(e)
        )

    return None, None


# =========================================================
# CHECKOUT VIEWS - PRODUCTION READY
# =========================================================

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)

from admin_dashboard.models import DeliveryHub

from payments.models import PaymentMethod

from .models import (
    Address,
    CartItem,
    Order,
    OrderItem
)

from .utils import calculate_shipping_cost

# =========================================================
# CART CHECKOUT (PRODUCTION READY)
# =========================================================
from payments.models import Payment


@login_required
def cart_checkout(request):

    user = request.user

    # =====================================================
    # ACTIVE HUB (SESSION SOURCE OF TRUTH)
    # =====================================================

    session_hub_id = request.session.get(
        "active_hub_id"
    )

    if not session_hub_id:

        messages.error(
            request,
            "Please select delivery location first."
        )

        return redirect(
            "where_we_deliver"
        )

    cart_hub = DeliveryHub.objects.filter(
        id=session_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    if not cart_hub:

        messages.error(
            request,
            "Selected delivery hub unavailable."
        )

        return redirect(
            "where_we_deliver"
        )

    # =====================================================
    # CART ITEMS (STRICT HUB FILTER)
    # =====================================================

    cart_items = (
        CartItem.objects
        .select_related(
            "product",
            "variant",
            "inventory",
            "inventory__shop",
            "inventory__shop__hub"
        )
        .filter(
            user=user,
            hub=cart_hub
        )
    )

    if not cart_items.exists():

        messages.error(
            request,
            "Your basket is empty."
        )

        return redirect(
            "cart_view"
        )

    # =====================================================
    # USER ADDRESSES
    # =====================================================

    user_addresses = (
        Address.objects
        .filter(
            customer__user=user,
            is_active=True
        )
        .order_by(
            "-is_default",
            "-id"
        )
    )
    if not user_addresses.exists():

        messages.info(
            request,
            "Please add a delivery address."
        )

        return redirect(
            f"{reverse('address_create')}?next={request.get_full_path()}"
        )
    
    for item in cart_items:
        item.line_total = Decimal(str(item.unit_price or 0)) * item.quantity

    # =====================================================
    # PAYMENT METHODS
    # =====================================================

    payment_methods = (
        PaymentMethod.objects
        .filter(
            is_active=True
        )
        .order_by(
            "sort_order"
        )
    )

    # =====================================================
    # SUBTOTAL
    # =====================================================

    sub_total = sum(
        Decimal(str(item.unit_price or 0))
        * item.quantity
        for item in cart_items
    )

    order_totals = {

        "sub_total": sub_total,

        "shipping_cost": Decimal("0.00"),

        "final_total": sub_total
    }

    # =====================================================
    # POST → PLACE ORDER
    # =====================================================

    if request.method == "POST":

        address_id = request.POST.get(
            "address_id"
        )

        payment_id = request.POST.get(
            "payment_method"
        )

        # =================================================
        # BASIC VALIDATION
        # =================================================

        if not address_id or not payment_id:

            messages.error(
                request,
                "Please select address and payment method."
            )

            return redirect(
                "cart_checkout"
            )

        # =================================================
        # ADDRESS VALIDATION
        # =================================================

        address = get_object_or_404(
            Address,
            id=address_id,
            customer__user=user,
            is_active=True
        )

        # =================================================
        # PAYMENT METHOD
        # =================================================

        payment_method = get_object_or_404(
            PaymentMethod,
            id=payment_id,
            is_active=True
        )

        # =================================================
        # DELIVERY VALIDATION
        # =================================================

        shipping_data = calculate_shipping_cost(
            address=address,
            delivery_hub=cart_hub
        )

        if shipping_data.get("error"):

            messages.error(
                request,
                shipping_data.get(
                    "message",
                    "Delivery unavailable."
                )
            )

            return redirect(
                "cart_checkout"
            )

        shipping_cost = Decimal(
            str(
                shipping_data.get(
                    "customer_fee",
                    0
                )
            )
        )

        final_total = (
            sub_total + shipping_cost
        )

        # =================================================
        # ORDER TRANSACTION
        # =================================================

        try:

            with transaction.atomic():

                # =========================================
                # CREATE ORDER
                # =========================================

                order = Order.objects.create(

                    user=user,

                    address=address,

                    hub=cart_hub,

                    subtotal=sub_total,

                    shipping_cost=shipping_cost,

                    total=final_total,

                    status="pending"
                )

                # =========================================
                # PROCESS CART ITEMS
                # =========================================

                for item in cart_items:

                    # -------------------------------------
                    # LOCK INVENTORY ROW
                    # -------------------------------------

                    inventory = (
                        Inventory.objects
                        .select_for_update()
                        .select_related(
                            "shop",
                            "shop__hub"
                        )
                        .get(
                            pk=item.inventory_id
                        )
                    )

                    # -------------------------------------
                    # HUB SECURITY
                    # -------------------------------------

                    if inventory.shop.hub_id != cart_hub.id:

                        raise Exception(
                            f"{item.product.name} "
                            f"is unavailable in "
                            f"selected delivery area."
                        )

                    # -------------------------------------
                    # INVENTORY EXISTS
                    # -------------------------------------

                    if inventory.stock <= 0:

                        raise Exception(
                            f"{item.product.name} "
                            f"is out of stock."
                        )

                    # -------------------------------------
                    # MAX ALLOWED QUANTITY
                    # -------------------------------------

                    allowed_quantity = min(
                        inventory.stock,
                        inventory.max_order_quantity
                    )

                    if item.quantity > allowed_quantity:

                        raise Exception(
                            f"Maximum "
                            f"{allowed_quantity} item(s) "
                            f"allowed for "
                            f"{item.product.name}."
                        )

                    # -------------------------------------
                    # REDUCE STOCK
                    # -------------------------------------

                    inventory.reduce_stock(
                        item.quantity,
                        reason="ORDER_PLACED",
                        note=f"Order #{order.id}"
                    )

                    # -------------------------------------
                    # CREATE ORDER ITEM
                    # -------------------------------------

                    OrderItem.objects.create(

                        order=order,

                        product=item.product,

                        variant=item.variant,

                        inventory=inventory,

                        quantity=item.quantity,

                        price=item.unit_price,

                        variant_name=getattr(
                            item.variant,
                            "display_name",
                            ""
                        )
                    )
                    # =========================================
                    # CREATE PAYMENT RECORD
                    # =========================================

                    Payment.objects.create(

                        order=order,

                        method=payment_method,

                        amount=final_total,

                        status="pending"

                    )

                # =========================================
                # CLEAR HUB CART
                # =========================================

                cart_items.delete()

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

            return redirect(
                "cart_checkout"
            )

        # =================================================
        # PAYMENT FLOW
        # =================================================

        if payment_method.name.lower() == "cod":

            messages.success(
                request,
                "Order placed successfully."
            )

            return redirect(
                "order_detail",
                order_id=order.id
            )

        return redirect(
            "payment",
            order_id=order.id
        )

    # =====================================================
    # PAGE RENDER
    # =====================================================

    return render(
        request,
        "shop/checkout_cart.html",
        {
            "cart_items": cart_items,
            "user_addresses": user_addresses,
            "payment_methods": payment_methods,
            "active_hub": cart_hub,
            "order_totals": order_totals
        }
    )


# =========================================================
# AJAX SHIPPING CALCULATION
# =========================================================

@login_required
def get_shipping_cost(request):

    user = request.user

    # =====================================================
    # ACTIVE HUB
    # =====================================================

    session_hub_id = request.session.get(
        "active_hub_id"
    )

    if not session_hub_id:

        return JsonResponse({
            "success": False,
            "message": "Please select delivery location first."
        })

    cart_hub = DeliveryHub.objects.filter(
        id=session_hub_id,
        is_active=True,
        is_accepting_orders=True
    ).first()

    if not cart_hub:

        return JsonResponse({
            "success": False,
            "message": "Delivery hub unavailable."
        })

    # =====================================================
    # CART ITEMS
    # =====================================================

    cart_items = CartItem.objects.filter(
        user=user
    )

    if not cart_items.exists():

        return JsonResponse({
            "success": False,
            "message": "Cart is empty."
        })

    # =====================================================
    # ADDRESS
    # =====================================================

    address_id = request.GET.get(
        "address_id"
    )

    if not address_id:

        return JsonResponse({
            "success": False,
            "message": "Address not selected."
        })

    try:

        address = Address.objects.get(
            id=address_id,
            customer__user=user,
            is_active=True
        )

    except Address.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": "Invalid address."
        })

    # =====================================================
    # SHIPPING ENGINE
    # =====================================================

    shipping_data = calculate_shipping_cost(
        address=address,
        delivery_hub=cart_hub
    )

    if shipping_data.get("error"):

        return JsonResponse({
            "success": False,
            "message": shipping_data.get(
                "message",
                "Delivery unavailable"
            )
        })

    # =====================================================
    # TOTALS
    # =====================================================

    subtotal = sum(
        Decimal(str(item.unit_price or 0))
        * item.quantity
        for item in cart_items
    )

    shipping_cost = Decimal(
        str(
            shipping_data.get(
                "customer_fee",
                0
            )
        )
    )

    final_total = (
        subtotal + shipping_cost
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse({

        "success": True,

        "sub_total": float(subtotal),

        "shipping_cost": float(shipping_cost),

        "final_total": float(final_total),

        "distance": float(
            shipping_data.get(
                "distance_km",
                0
            )
        ),

        "hub": cart_hub.name
    })
#===========================================================

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import render


@login_required
def order_list(request):

    order_items_qs = (
        OrderItem.objects
        .select_related(
            "product",
            "variant",
            "inventory"
        )
        .prefetch_related(
            "product__product_images"
        )
    )

    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related(
            "address",
            "shop",
            "hub"
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=order_items_qs
            )
        )
        .order_by("-placed_at")
    )

    print("TOTAL ORDERS =>", orders.count())

    paginator = Paginator(orders,8)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "total_orders": orders.count(),
        "active_orders": orders.exclude(
            status__in=[
                "delivered",
                "cancelled",
                "declined"
            ]
        ).count(),
        "delivered_orders": orders.filter(
            status="delivered"
        ).count(),
    }

    return render(
        request,
        "shop/order_list.html",
        context
    )




#==================================================================

from django.shortcuts import get_object_or_404, render
from django.db.models import Prefetch

from .models import (
Order,
OrderItem,
Rating,
)

from payments.models import Payment

def order_detail(request, order_id):


# =====================================================
# OPTIMIZED ORDER QUERY
# =====================================================

    order = get_object_or_404(

        Order.objects.select_related(

            # -----------------------------------------
            # ADDRESS
            # -----------------------------------------

            "address",

            # -----------------------------------------
            # RIDER (future live tracking)
            # -----------------------------------------

            "delivery",

        ).prefetch_related(

            # -----------------------------------------
            # ORDER ITEMS + PRODUCT IMAGES
            # -----------------------------------------

            Prefetch(

                "items",

                queryset=OrderItem.objects.select_related(
                    "product"
                ).prefetch_related(
                    "product__product_images"
                )

            ),

            # -----------------------------------------
            # PAYMENTS
            # -----------------------------------------

            Prefetch(

                "payments",

                queryset=Payment.objects.select_related(
                    "method"
                )

            ),

        ),

        id=order_id,
        user=request.user

    )

    # =====================================================
    # ORDER ITEMS
    # =====================================================

    order_items = order.items.all()

    # =====================================================
    # RATED PRODUCTS
    # =====================================================

    product_ids = [

        item.product_id
        for item in order_items

    ]

    rated_products = list(

        Rating.objects.filter(

            user=request.user,
            product_id__in=product_ids

        ).values_list(

            "product_id",
            flat=True

        )

    )

    # =====================================================
    # PRIMARY PAYMENT
    # =====================================================

    payment = order.payments.first()

    # =====================================================
    # LIVE TRACKING
    # =====================================================

    can_track_live = (

        order.status in [

            "assigned",
            "out_for_delivery"

        ]

    )

    # =====================================================
    # OTP VISIBILITY
    # =====================================================

    show_delivery_otp = bool(

        order.delivery_token

    )

    # =====================================================
    # POST DELIVERY ACTIONS
    # =====================================================

    can_review = (

        order.status == "delivered"

    )

    # =====================================================
    # SUPPORT ACCESS
    # =====================================================

    support_enabled = True

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "order": order,

        "order_items": order_items,

        "payment": payment,

        "rated_products": rated_products,

        "can_track_live": can_track_live,

        "show_delivery_otp": show_delivery_otp,

        "can_review": can_review,

        "support_enabled": support_enabled,

    }

    return render(

        request,

        "order/order_detail.html",

        context

    )



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