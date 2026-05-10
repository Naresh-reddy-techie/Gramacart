import json
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import localdate
from django.contrib.auth.models import User, Group
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Model & Form Imports
from .forms import (
    DeliveryBoyCreateForm, DeliveryBoyUpdateForm, 
    ProofUploadForm, ManualAssignForm, DeliveryProfileForm
)
from .models import Delivery, DeliveryProfile, DeliveryStatus
from admin_dashboard.models import DeliveryHub
from payments.models import Payment
from shop.models import Order

# ------------------- 1. ACCESS CONTROL -------------------

def delivery_boy_required(view_func):
    """Ensures only members of the 'DeliveryBoy' group can access rider views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name='DeliveryBoy').exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access restricted to Delivery Partners.")
        return redirect('login')
    return wrapper


# ------------------- 2. AUTHENTICATION -------------------

def login_user(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='DeliveryBoy').exists():
            return redirect('rider_dashboard')
        return redirect('user_signup')

    if request.method == "POST":
        u_name = request.POST.get("username")
        p_word = request.POST.get("password")
        user = authenticate(request, username=u_name, password=p_word)
        
        if user:
            login(request, user)
            if user.groups.filter(name='DeliveryBoy').exists():
                return redirect('rider_dashboard')
            return redirect('admin_delivery_list')
        messages.error(request, "Invalid username or password.")
            
    return redirect('user_signin')

def logout_view(request):
    logout(request)
    return redirect('login')


# ------------------- 3. ADMIN: FLEET & OPERATIONS -------------------

@login_required
def list_delivery_boys(request):
    """List all partners and their current availability."""
    profiles = DeliveryProfile.objects.select_related('user', 'hub').all()
    busy_ids = Delivery.objects.filter(
        status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.OUT]
    ).values_list('delivery_boy_id', flat=True)

    return render(request, 'delivery_portal/delivery_boy_list.html', {
        'delivery_profiles': profiles,
        'busy_ids': list(busy_ids)
    })

@login_required
def add_delivery_boy(request):
    """Handles manual creation of delivery partners and their profiles."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        hub_id = request.POST.get('hub')
        
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=request.POST.get('first_name'),
                    last_name=request.POST.get('last_name')
                )
                # Ensure they belong to the correct group
                group, _ = Group.objects.get_or_create(name='DeliveryBoy')
                user.groups.add(group)

                hub = DeliveryHub.objects.get(id=hub_id)
                DeliveryProfile.objects.create(
                    user=user,
                    hub=hub,
                    is_active=request.POST.get('is_active') == 'on'
                )

            request.session['onboarding_data'] = {'username': username, 'password': password, 'hub': hub.name}
            return redirect('onboarding_success')

        except Exception as e:
            messages.error(request, f"Error creating partner: {str(e)}")
    
    hubs = DeliveryHub.objects.all().order_by('name')
    return render(request, 'delivery_portal/add_delivery_boy.html', {'hubs': hubs})

@login_required
def admin_delivery_list(request):
    """Master view for Admins to monitor all deliveries."""
    deliveries = Delivery.objects.select_related('order', 'delivery_boy', 'nearest_hub').all().order_by('-id')
    return render(request, 'delivery_portal/admin_delivery_list.html', {'deliveries': deliveries})

@login_required
def manual_assign_delivery(request, delivery_id):
    """Admin manually assigns a rider to a delivery."""
    delivery = get_object_or_404(Delivery, id=delivery_id)
    if request.method == 'POST':
        form = ManualAssignForm(request.POST)
        if form.is_valid():
            rider = form.cleaned_data['delivery_boy']
            delivery.delivery_boy = rider
            delivery.status = DeliveryStatus.ASSIGNED
            delivery.assigned_at = timezone.now()
            delivery.save()
            messages.success(request, f"Assigned to {rider.username}")
            return redirect('admin_delivery_list')
    else:
        form = ManualAssignForm()
    return render(request, 'delivery_portal/manual_assign.html', {'form': form, 'delivery': delivery})


# ------------------- 4. RIDER: DASHBOARD & ACTIONS -------------------
from django.utils.timezone import localdate
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import Delivery, DeliveryStatus
from payments.models import FinancialWallet


# -----------------------------
# SERIALIZER (RADAR FORMAT)
# -----------------------------
def serialize_delivery(d):

    order = getattr(d, "order", None)

    if not order:
        return {
            "id": d.id,
            "order_number": None,
            "earnings": float(d.rider_earning or 0),
            "pickup": {"hub_name": "Hub"},
            "drop": {},
            "items": [],
            "status": d.status,
        }

    address = getattr(order, "address", None)

    items = list(
        order.items.select_related("product").all()
    )

    return {
        "id": d.id,
        "order_number": order.order_number,

        "pickup": {
            "hub_name": d.nearest_hub.name if d.nearest_hub else "Hub",
        },

        "drop": {
            "name": address.recipient_name if address else "Customer",
            "phone": address.phone_number if address else "",
            "full_address": (
                f"{address.address_line or ''} {address.landmark or ''} "
                f"{address.city or ''} {address.state or ''} {address.pincode or ''}"
                if address else ""
            ),
            "lat": float(address.latitude) if address else None,
            "lng": float(address.longitude) if address else None,
        },

        "items": [
            {
                "name": i.product.name,
                "qty": i.quantity,
                "size": i.product.size,
            }
            for i in items
        ],

        "status": d.status,
    }
# -----------------------------
# DASHBOARD VIEW
# -----------------------------
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, time

# Assuming your decorators and models are imported correctly
# from .models import Delivery, DeliveryStatus, FinancialWallet

@login_required
@delivery_boy_required
def dashboard(request):
    profile = getattr(request.user, 'delivery_profile', None)
    if not profile:
        messages.error(request, "Delivery profile not found.")
        return redirect('login')

    # -------------------------
    # 1. DATE PARSING & TIMEZONE WINDOW
    # -------------------------
    selected_date_str = request.GET.get('date')
    try:
        if selected_date_str:
            target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.localdate()
    except (ValueError, TypeError):
        target_date = timezone.localdate()

    # Create a range from 00:00:00 to 23:59:59 in Asia/Kolkata time
    # This solves the "0 earnings" issue caused by UTC vs IST mismatch
    start_of_day = timezone.make_aware(datetime.combine(target_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(target_date, time.max))

    # -------------------------
    # 2. ACTIVE TASKS (Always Live)
    # -------------------------
    active_qs = Delivery.objects.filter(
        delivery_boy=request.user
    ).select_related('order', 'order__address', 'nearest_hub')

    deliveries_assigned = active_qs.filter(status=DeliveryStatus.ASSIGNED)
    deliveries_out = active_qs.filter(status=DeliveryStatus.OUT)

    # Pickup timer logic
    for d in deliveries_assigned:
        if d.assigned_at:
            elapsed = timezone.now() - d.assigned_at
            remaining = 20 - int(elapsed.total_seconds() / 60)
            d.pickup_minutes_left = max(0, remaining)
            d.is_overdue = remaining <= 0
        else:
            d.pickup_minutes_left = 20
            d.is_overdue = False

    # -------------------------
    # 3. RADAR ORDERS (Marketplace)
    # -------------------------
    available_orders_qs = Delivery.objects.filter(
        status=DeliveryStatus.PACKED,
        nearest_hub=profile.hub,
        delivery_boy__isnull=True
    ).select_related('order', 'order__address', 'nearest_hub').order_by('-id')

    # -------------------------
    # 4. HISTORY & PERFORMANCE (Filtered by Range)
    # -------------------------
    # We use delivered_at because that's when the money is actually earned
    delivered_history = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.DELIVERED,
        delivered_at__range=(start_of_day, end_of_day)
    )

    cancelled_count = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.CANCELLED,
        created_at__range=(start_of_day, end_of_day)
    ).count()

    # Calculate Totals
    day_earnings = delivered_history.aggregate(total=Sum('rider_earning'))['total'] or 0
    day_cash = delivered_history.filter(
        cod_collected=True
    ).aggregate(total=Sum('order__total'))['total'] or 0

    from admin_dashboard.models import CompanyInfo  
    company = CompanyInfo.objects.first()

    # -------------------------
    # 5. CONTEXT & WALLET
    # -------------------------
    wallet, _ = FinancialWallet.objects.get_or_create(user=request.user)

    context = {
        "profile": profile,
        "company": company,
        # JSON Data for JS (Radar & Tasks)
        "available_orders": [serialize_delivery(d) for d in available_orders_qs],
        "assigned_orders_json": [serialize_delivery(d) for d in deliveries_assigned],
        "out_orders_json": [serialize_delivery(d) for d in deliveries_out],

        # Performance Stats (Passed to UI Cards)
        "wallet_balance": wallet.pending_balance,
        "day_earnings": day_earnings,
        "orders_delivered": delivered_history.count(),
        "orders_cancelled": cancelled_count,
        "cash_in_hand": day_cash,

        # UI Helpers
        "total_active_tasks": deliveries_assigned.count() + deliveries_out.count(),
        "today": timezone.localdate().isoformat(),
        "selected_date": target_date.isoformat(),
    }
    
  
    return render(request, "delivery_portal/dashboard.html", context)

from .utils import sync_order_status
@login_required
@delivery_boy_required
def confirm_pickup(request, delivery_id):
    """
    Rider at the Hub: Confirms they have the items.
    Moves status to OUT, activating the Route/Call buttons on the Dashboard.
    """
    # 1. Fetch delivery and ensure it belongs to the current user
    delivery = get_object_or_404(
        Delivery.objects.select_related('order', 'delivery_boy__delivery_profile'), 
        pk=delivery_id, 
        delivery_boy=request.user
    )

    # 2. Safety Check: Is the rider actually 'Online'?
    profile = request.user.delivery_profile
    if not profile.is_online:
        messages.error(request, "You must be ONLINE to start a delivery.")
        return redirect('rider_dashboard')

    # 3. Logic Check: Is it actually waiting for pickup?
    if delivery.status != DeliveryStatus.ASSIGNED:
        messages.warning(request, "This order has already been picked up or is in an invalid state.")
        return redirect('rider_dashboard')

    try:
        with transaction.atomic():
            # 4. Update Delivery state
            delivery.status = DeliveryStatus.OUT
            delivery.out_for_delivery_at = timezone.now()
            delivery.save()
            
            # 5. Update Order state (Customer now sees 'Out for Delivery')
            # sync_order_status should be robust enough to handle the 'out_for_delivery' string
            sync_order_status(delivery.order, 'out_for_delivery')
            
            # OPTIONAL: Log location at pickup for audit trail
            # if delivery.order.current_lat: ... (capture hub location)

        messages.success(request, f"Order #{delivery.order.order_number} Picked Up! Drive safely to {delivery.order.address.village_name}.")
        
    except Exception as e:
        # If something goes wrong with the DB, catch it so the app doesn't crash
        messages.error(request, "System error confirming pickup. Please try again.")
        print(f"Pickup Error: {e}") # Log this to your server console

    return redirect('delivery_complete', delivery_id=delivery.id)



import traceback
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Delivery, DeliveryStatus

def mark_delivery_failed(request, delivery_id):
    try:
        # 1. Fetch delivery with related order and the user profile
        delivery = get_object_or_404(
            Delivery.objects.select_related('order', 'delivery_boy__delivery_profile'), 
            id=delivery_id
        )
        
        if request.method == "POST":
            reason = request.POST.get('reason')
            
            if not reason:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Reason is required'}, status=400)
                messages.error(request, "Please provide a reason.")
                return redirect('rider_dashboard')

            # 2. Update Delivery status to CANCELLED (per your DeliveryStatus choices)
            delivery.status = DeliveryStatus.CANCELLED
            delivery.tracking_notes = f"FAILURE REASON: {reason}" 
            delivery.save()
            
            # 3. Update Order status
            if delivery.order:
                order = delivery.order
                order.status = 'cancelled' # Ensure 'cancelled' is in your Order model choices
                order.save()
            
            # 4. Set Rider back to Online (Available for new tasks)
            if delivery.delivery_boy and hasattr(delivery.delivery_boy, 'delivery_profile'):
                profile = delivery.delivery_boy.delivery_profile
                profile.is_online = True 
                profile.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Task cancelled successfully.'
                })
            
            messages.warning(request, "Task cancelled. Please return the items.")
            return redirect('rider_dashboard')

    except Exception as e:
        print("--- GRAMACART SERVER ERROR ---")
        print(traceback.format_exc()) 
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

import urllib.parse
import base64
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required



import qrcode
from io import BytesIO

def generate_upi_qr_code(upi_id, payee_name, amount):
    """
    Generates a UPI QR code and returns it as a BytesIO stream
    to match the .read() requirement in the view.
    """
    # Construct the UPI string
    # pn: Payee Name, pa: Payee Address (UPI ID), am: Amount, cu: Currency
    upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR"
    
    # Generate the QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to a BytesIO buffer so it can be .read() like a file
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)  # Reset pointer to the start
    return buffer

@login_required
@delivery_boy_required
def complete_delivery(request, delivery_id):
    # 1. Corrected Query: Removed 'order__payment_method' 
    # because it doesn't exist on the Order model.
    delivery = get_object_or_404(
        Delivery.objects.select_related('order').prefetch_related('order__payments__method'), 
        pk=delivery_id, 
        delivery_boy=request.user
    )
    
    order = delivery.order
    
    if delivery.status == DeliveryStatus.DELIVERED:
        messages.warning(request, "This order is already settled.")
        return redirect('rider_dashboard')

    # 2. Logic to find the intended UPI method
    # We look at the last payment attempt associated with this order
    last_payment = order.payments.last()
    upi_method = None
    upi_uri = ""
    upi_qr_base64 = None
    
    # Check if the last payment used was UPI
    if last_payment and last_payment.method.name.lower() == 'upi':
        upi_method = last_payment.method
    else:
        # Fallback: If no payment exists yet, find the active UPI method
        from payments.models import PaymentMethod
        upi_method = PaymentMethod.objects.filter(name='upi', is_active=True).first()

    # 3. Generate QR if order isn't already paid
    if not order.is_paid and upi_method:
        upi_id = upi_method.config.get('upi_id')
        payee_name = upi_method.config.get('payee_name', 'GramaCart')
        
        # Intent URI
        payee_encoded = urllib.parse.quote(payee_name)
        upi_uri = f"upi://pay?pa={upi_id}&pn={payee_encoded}&am={order.total}&cu=INR"
        
        # QR Base64
        qr_file = generate_upi_qr_code(upi_id, payee_name, order.total)
        upi_qr_base64 = base64.b64encode(qr_file.read()).decode()

    # 4. Form Processing
    if request.method == 'POST':
        form = ProofUploadForm(request.POST, request.FILES, instance=delivery)
        entered_token = request.POST.get('order_token')
        entered_utr = request.POST.get('transaction_id')

        # PIN Verification
        if entered_token != order.delivery_token:
            messages.error(request, "Invalid Delivery Token! Check the customer's PIN.")
            return render(request, 'delivery_portal/complete_delivery.html', {
                'delivery': delivery, 'form': form, 'upi_uri': upi_uri, 
                'upi_qr_base64': upi_qr_base64, 'upi_id': upi_id if upi_method else None
            })

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Handle UPI Payment Record if Rider provided a UTR
                    if entered_utr and not order.is_paid:
                        from .models import Payment
                        Payment.objects.create(
                            order=order,
                            method=upi_method,
                            amount=order.total,
                            transaction_id=entered_utr,
                            status='pending'
                        )

                    delivery = form.save(commit=False)
                    delivery.status = DeliveryStatus.DELIVERED
                    delivery.delivered_at = timezone.now()
                    delivery.save()
                    
                    # Update Order status
                    order.status = 'delivered'
                    order.save()

                messages.success(request, f"Order #{order.order_number} Delivered!")
                return redirect('rider_dashboard')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        form = ProofUploadForm(instance=delivery)
    
    return render(request, 'delivery_portal/complete_delivery.html', {
        'delivery': delivery, 
        'form': form,
        'upi_uri': upi_uri,
        'upi_qr_base64': upi_qr_base64,
        'upi_id': upi_method.config.get('upi_id') if upi_method else None
    })

"""
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render

@login_required
@delivery_boy_required
def complete_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related('order').prefetch_related('order__payments'), 
        pk=delivery_id, 
        delivery_boy=request.user
    )
    
    # 1. Prevent double settlement
    if delivery.status == DeliveryStatus.DELIVERED:
        messages.warning(request, "This order is already settled.")
        return redirect('rider_dashboard')

    if request.method == 'POST':
        form = ProofUploadForm(request.POST, request.FILES, instance=delivery)
        entered_token = request.POST.get('order_token') # Grab the 4 digits from the UI
        
        # 2. TOKEN VERIFICATION CHECK
        if entered_token != delivery.order.delivery_token:
            messages.error(request, "Invalid Delivery Token! Please ask the customer for the correct 4-digit PIN.")
            return render(request, 'delivery_portal/complete_delivery.html', {
                'delivery': delivery, 
                'form': form,
                'error': True
            })

        # 3. PROOF & SETTLEMENT LOGIC
        if form.is_valid():
            try:
                with transaction.atomic():
                    delivery = form.save(commit=False)
                    delivery.status = DeliveryStatus.DELIVERED
                    delivery.delivered_at = timezone.now()
                    delivery.save()
                    
                    # RUN THE MONEY SETTLEMENT BRAIN
                    settle_order_funds(delivery)
                    
                    # Update Order Status for the Customer App
                    sync_order_status(delivery.order, DeliveryStatus.DELIVERED)

                messages.success(request, f"Order #{delivery.order.order_number} Delivered! Funds distributed.")
                return redirect('rider_dashboard')
            
            except Exception as e:
                messages.error(request, "Settlement failed. Please contact admin.")
                # Log error here
    else:
        form = ProofUploadForm(instance=delivery)
    
    return render(request, 'delivery_portal/complete_delivery.html', {'delivery': delivery, 'form': form})
"""
    
from django.db.models import Sum
from django.utils.timezone import localdate, make_aware
import datetime as dt_module  # Use an alias to prevent clashes
from datetime import timedelta
from itertools import groupby
from .models import Delivery, DeliveryStatus

@login_required
@delivery_boy_required
def rider_earnings(request):
    today_date = localdate()
    selected_month_str = request.GET.get('month', today_date.strftime('%Y-%m'))
    
    try:
        # We use unique names so they never match 'datetime' or 'date'
        y_val, m_val = map(int, selected_month_str.split('-'))
    except (ValueError, AttributeError):
        y_val, m_val = today_date.year, today_date.month

    # Logic using the alias 'dt_module'
    start_date = dt_module.date(y_val, m_val, 1)
    if m_val == 12:
        end_date = dt_module.date(y_val + 1, 1, 1)
    else:
        end_date = dt_module.date(y_val, m_val + 1, 1)

    # Filtering
    deliveries = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.DELIVERED,
        delivered_at__gte=make_aware(dt_module.datetime.combine(start_date, dt_module.time.min)),
        delivered_at__lt=make_aware(dt_module.datetime.combine(end_date, dt_module.time.min))
    ).select_related('order', 'order__address').order_by('-delivered_at')

    # Calculations with Null-safety
    total_balance = sum(d.rider_earning for d in deliveries if d.rider_earning)
    
    # Line 587 area - Fixed by using explicit checks and alias
    today_earnings = sum(
        d.rider_earning for d in deliveries 
        if d.delivered_at and d.delivered_at.date() == today_date
    )
    
    start_of_week = today_date - timedelta(days=today_date.weekday())
    weekly_earnings = sum(
        d.rider_earning for d in deliveries 
        if d.delivered_at and d.delivered_at.date() >= start_of_week
    )

    # Grouping
    history_groups = []
    for date_key, items in groupby(deliveries, lambda x: x.delivered_at.date() if x.delivered_at else None):
        if date_key is None:
            continue
        
        items_list = list(items)
        history_groups.append({
            'date': date_key,
            'day_total': sum(item.rider_earning for item in items_list if item.rider_earning),
            'deliveries': items_list
        })

    context = {
        'today': today_date,
        'current_month': selected_month_str,
        'total_balance': total_balance,
        'today_earnings': today_earnings,
        'weekly_earnings': weekly_earnings,
        'history_groups': history_groups,
    }
    return render(request, 'delivery_portal/rider_earnings.html', context)
@csrf_exempt
@login_required
@delivery_boy_required
def update_rider_location(request, delivery_id):
    """API endpoint for the rider's phone to send GPS updates."""
    if request.method == "POST":
        delivery = get_object_or_404(Delivery, pk=delivery_id, delivery_boy=request.user)
        try:
            data = json.loads(request.body)
            delivery.current_lat = data.get('lat')
            delivery.current_lng = data.get('lng')
            delivery.save(update_fields=['current_lat', 'current_lng', 'last_location_update'])
            return JsonResponse({'status': 'success'})
        except Exception:
            return JsonResponse({'status': 'error'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@login_required
@delivery_boy_required
def delivery_failed(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id, delivery_boy=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        
        try:
            with transaction.atomic():
                # 1. Update Delivery
                delivery.status = DeliveryStatus.CANCELLED 
                delivery.tracking_notes = f"FAILED: {reason}"
                delivery.save()
                
                # 2. Update Order (Double check if 'status' is the correct field name)
                order = delivery.order
                order.status = 'CANCELLED' # Use the exact string your model expects
                order.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
                
            messages.warning(request, f"Order #{delivery.order.id} marked as failed.")
            return redirect('rider_dashboard')

        except Exception as e:
            # This will print the exact error to your terminal
            print(f"CRITICAL ERROR IN CANCEL: {str(e)}") 
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            raise e # Re-raise for non-ajax debugging
            
    return render(request, 'delivery_portal/delivery_failed.html', {'delivery': delivery})

@login_required
@delivery_boy_required
def rider_active_deliveries(request):
    """
    Focused view for the 'Live Radar'. 
    Ensures coordinates and full address are available for the Route Map.
    """
    active_deliveries = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.OUT
    ).select_related(
        'order', 
        'order__address', 
        'nearest_hub'
    )

    return render(request, 'delivery_portal/active_deliveries.html', {
        'deliveries': active_deliveries
    })

# 2. Add this to handle the onboarding success screen
@login_required
def onboarding_success(request):
    """View to show newly created rider credentials for sharing via WhatsApp."""
    onboarding_data = request.session.get('onboarding_data')
    
    if not onboarding_data: 
        return redirect('delivery_boy_list')
        
    return render(request, 'delivery_portal/onboarding_success.html', {
        'onboarding_data': onboarding_data
    })

# 3. Add these for the Admin CRUD operations (Update/Delete)
@login_required
def update_delivery_boy(request, user_id):
    """Admin view to update a rider's profile, hub, and status."""
    rider_user = get_object_or_404(User, id=user_id)
    profile = getattr(rider_user, 'delivery_profile', None)
    
    if request.method == 'POST':
        form = DeliveryBoyUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profile for {rider_user.username} updated.")
            return redirect('delivery_boy_list')
    else:
        form = DeliveryBoyUpdateForm(instance=profile)
        
    return render(request, 'delivery_portal/update_rider.html', {
        'form': form,
        'rider_user': rider_user
    })

@login_required
def delete_delivery_boy(request, profile_id):
    """Admin view to remove a delivery partner profile."""
    profile = get_object_or_404(DeliveryProfile, id=profile_id)
    rider_name = profile.user.username
    
    if request.method == 'POST':
        # We delete the profile, but usually keep the User for record integrity
        # or delete both depending on your preference.
        profile.user.delete() 
        messages.success(request, f"Partner {rider_name} removed.")
        return redirect('delivery_boy_list')
        
    return render(request, 'delivery_portal/delete_rider_confirm.html', {'profile': profile})

# 4. Add this to manually trigger a delivery from the Order admin
@login_required
def create_delivery_from_order(request, order_id):
    """Admin view to manually create a delivery object for a specific order."""
    order = get_object_or_404(Order, id=order_id)
    
    if hasattr(order, 'delivery'):
        messages.info(request, f"Delivery already exists for Order #{order.id}")
    else:
        Delivery.objects.create(order=order, status=DeliveryStatus.PENDING)
        messages.success(request, f"Delivery task created for Order #{order.id}")
        
    return redirect('admin_delivery_list')

@login_required
@delivery_boy_required
def rider_profile(request):
    """
    Shows the delivery partner's personal details, 
    assigned village hub, and vehicle information.
    """
    # Safely get the profile or None if it doesn't exist
    profile = getattr(request.user, 'delivery_profile', None)
    
    return render(request, 'delivery_portal/rider_profile.html', {
        'profile': profile,
        'user': request.user
    })

@login_required
def update_delivery_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            delivery_id = data.get('delivery_id')
            new_status = data.get('status') # e.g., 'delivered'

            delivery = Delivery.objects.get(id=delivery_id, delivery_boy=request.user)
            delivery.status = new_status
            
            # If marking as delivered, set the timestamp for your earnings logic
            if new_status == DeliveryStatus.DELIVERED:
                delivery.delivered_at = timezone.now()
            
            delivery.save()

            return JsonResponse({'status': 'success', 'message': 'Order updated!'})
        except Delivery.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Delivery not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)

import json
from django.http import JsonResponse
from payments.logic import settle_order_funds # Import our logic

def update_status_api(request):
    data = json.loads(request.body)
    order_num = data.get('order_number')
    new_status = data.get('status')
    
    delivery = Delivery.objects.get(order__order_number=order_num)
    delivery.status = new_status
    delivery.save()

    # CRITICAL: Trigger the Money Splitter when delivered
    if new_status == 'delivered':
        settle_order_funds(delivery) 

    return JsonResponse({'success': True})

@csrf_exempt
@login_required
@delivery_boy_required
def toggle_duty(request):
    """Updates the is_online status and records the timestamp."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            profile = request.user.delivery_profile
            profile.is_online = data.get('is_online', False)
            # You can also add profile.last_duty_toggle = timezone.now() here
            profile.save()
            return JsonResponse({'status': 'success', 'is_online': profile.is_online})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@login_required
@delivery_boy_required
@transaction.atomic  
def accept_order(request, delivery_id):
    """Moves an order from RADAR (Packed) to MY TASKS (Assigned)."""
    
    profile = request.user.delivery_profile

    # 1. Lock the row: Only look for PACKED orders that have NO rider
    try:
        delivery = Delivery.objects.select_for_update().get(
            id=delivery_id, 
            status=DeliveryStatus.PACKED,
            delivery_boy__isnull=True,
            nearest_hub=profile.hub # <--- Ensure rider belongs to this hub
        )
    except Delivery.DoesNotExist:
        messages.error(request, "Too late! Another rider already accepted this order.")
        return redirect('rider_dashboard')

    # 2. Online Check
    if not profile.is_online:
        messages.error(request, "You must be Online to accept orders!")
        return redirect('rider_dashboard')

    # 3. Perform the Assignment
    delivery.delivery_boy = request.user
    delivery.status = DeliveryStatus.ASSIGNED
    delivery.assigned_at = timezone.now()
    delivery.save()

    # 4. Sync the main Order status
    sync_order_status(delivery.order, DeliveryStatus.ASSIGNED)

    messages.success(request, f"Order #{delivery.order.order_number} is now in your tasks!")
    return redirect('rider_dashboard')

"""
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from datetime import datetime, time

@login_required
@delivery_boy_required
def check_new_orders(request):
    
    #Unified API for Rider Dashboard: 
    #- Parts A & B (Tasks/Radar) are ALWAYS LIVE.
    #- Part C (Stats) follows the CALENDAR DATE.
   
    profile = request.user.delivery_profile
    
    # --- PART 0: DATE PARSING & TIMEZONE WINDOW ---
    selected_date_str = request.GET.get('date')
    try:
        if selected_date_str:
            target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.localdate()
    except (ValueError, TypeError):
        target_date = timezone.localdate()

    # Create the Asia/Kolkata aware time range
    start_of_day = timezone.make_aware(datetime.combine(target_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(target_date, time.max))

    # --- PART A: ACTIVE TASKS (Always Live) ---
    my_active_tasks = Delivery.objects.filter(
        delivery_boy=request.user,
        status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.OUT]
    ).select_related('order__address', 'nearest_hub').prefetch_related('order__items__product')

    assigned_data = []
    out_data = []

    for d in my_active_tasks:
        addr = d.order.address
        hub = d.nearest_hub
        items_list = [
            {'name': i.product.name.upper(), 'qty': i.quantity, 'size': i.product.size} 
            for i in d.order.items.all()
        ]
        
        task_payload = {
            'id': d.id,
            'order_number': d.order.order_number,
            'status': d.status,
            'delivery_fee': str(d.rider_earning or "0"),
            'items': items_list,
            'pickup': {
                'name': hub.name.upper() if hub else "HUB",
                'address': f"{hub.name.upper()} CENTER" if hub else "MAIN HUB",
                'lat': str(hub.latitude) if hub else "0",
                'lng': str(hub.longitude) if hub else "0",
            },
            'drop': {
                'name': addr.recipient_name.upper() if addr else "CUSTOMER",
                'phone': addr.phone_number if addr else "",
                'village': addr.city.upper() if addr else "",
                'lat': str(addr.latitude) if addr else "0",
                'lng': str(addr.longitude) if addr else "0",
            }
        }
        if d.status == DeliveryStatus.ASSIGNED:
            assigned_data.append(task_payload)
        else:
            out_data.append(task_payload)

    # --- PART B: THE ORDER RADAR (Always Live) ---
    orders_data = []
    if profile.is_online and profile.hub:
        market_orders = Delivery.objects.filter(
            status__iexact=DeliveryStatus.PACKED, 
            nearest_hub=profile.hub,
            delivery_boy__isnull=True
        ).select_related('order__address', 'nearest_hub').order_by('-id')

        for d in market_orders:
            addr = d.order.address
            hub = d.nearest_hub

            radar_items = [
            {
                'name': i.product.name.upper(), 
                'qty': i.quantity, 
                'size': i.product.size if i.product.size else ""
            } 
            for i in d.order.items.all()
            ]

            orders_data.append({
                'id': d.id,
                'earnings': str(d.rider_earning or "0"),
                'village': addr.city.upper() if addr else "LOCAL",
                'hub_name': hub.name.upper() if hub else "HUB",
                'accept_url': reverse('accept_order', args=[d.id]),
                'items':radar_items,
                'pickup':{'hub_name':hub.name.upper() if hub else "HUB"},
                'drop':{'full_address':addr.get_full_address() if addr else "Address missing",'landmark':addr.landmark if addr else " "},

                'hub_lat': str(hub.latitude) if hub else "0",
                'hub_lng': str(hub.longitude) if hub else "0",
                'drop_lat': str(addr.latitude) if addr else "0",
                'drop_lng': str(addr.longitude) if addr else "0",
            })

    # --- PART C: PERFORMANCE STATS (Using Range) ---
    # Delivered stats use 'delivered_at'
    delivered_history = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.DELIVERED,
        delivered_at__range=(start_of_day, end_of_day)
    )

    # Cancelled stats use 'created_at' as they have no delivered_at timestamp
    cancelled_count = Delivery.objects.filter(
        delivery_boy=request.user,
        status=DeliveryStatus.CANCELLED,
        created_at__range=(start_of_day, end_of_day)
    ).count()

    # Calculations
    day_earnings = delivered_history.aggregate(total=Sum('rider_earning'))['total'] or 0
    day_cash = delivered_history.filter(
        cod_collected=True
    ).aggregate(total=Sum('order__total'))['total'] or 0

    return JsonResponse({
        'assigned': assigned_data,
        'out_deliveries': out_data,
        'orders': orders_data,
        
        # Numbers sent to JavaScript (Converted to float for JSON safety)
        'today_earnings': float(day_earnings),
        'orders_delivered': delivered_history.count(),
        'orders_cancelled': cancelled_count,
        'cash_to_pay': float(day_cash),
        
        'selected_date': target_date.isoformat(),
        'is_online': profile.is_online
    })
    

"""
from django.utils import timezone
from django.db.models import Sum, Q, Prefetch
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from datetime import datetime
import logging

# Set up logging to track errors in production without showing them to users
logger = logging.getLogger(__name__)

@login_required
@delivery_boy_required
def check_new_orders(request):
    """
    Final Production Version:
    - No attribute errors.
    - Optimized DB queries.
    - Safe field access.
    """
    profile = request.user.delivery_profile
    
    # --- DATE PARSING ---
    selected_date_str = request.GET.get('date')
    try:
        target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else timezone.localdate()
    except (ValueError, TypeError):
        target_date = timezone.localdate()

    # Create time boundaries for stats
    start_of_day = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))

    # --- PART A: ACTIVE TASKS ---
    my_active_tasks = Delivery.objects.filter(
        delivery_boy=request.user,
        status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.OUT]
    ).select_related('order__address', 'nearest_hub').prefetch_related('order__items__product')

    assigned_data, out_data = [], []

    for d in my_active_tasks:
        addr = d.order.address
        hub = d.nearest_hub
        
        # Build Address String Safely
        full_addr = f"{addr.address_line or ''}, {addr.city or ''} {addr.pincode or ''}".strip(", ") if addr else "N/A"
        
        payload = {
            'id': d.id,
            'order_number': d.order.order_number,
            'status': d.status,
            'earnings': str(d.rider_earning or "0"),
            'items': [{'name': i.product.name.upper(), 'qty': i.quantity} for i in d.order.items.all()],
            'pickup': {
                'hub_name': hub.name.upper() if hub else "HUB",
                'lat': str(hub.latitude) if hub else "0",
                'lng': str(hub.longitude) if hub else "0",
            },
            'drop': {
                'name': addr.recipient_name.upper() if addr else "CUSTOMER",
                'phone': addr.phone_number if addr else "",
                'full_address': full_addr,
                'landmark': addr.landmark if addr else "",
                'lat': str(addr.latitude) if addr else "0",
                'lng': str(addr.longitude) if addr else "0",
            }
        }
        assigned_data.append(payload) if d.status == DeliveryStatus.ASSIGNED else out_data.append(payload)

    # --- PART B: MARKET RADAR ---
    orders_data = []
    if profile.is_online and profile.hub:
        market_orders = Delivery.objects.filter(
            status__iexact=DeliveryStatus.PACKED,
            nearest_hub=profile.hub,
            delivery_boy__isnull=True
        ).select_related('order__address', 'nearest_hub')

        for d in market_orders:
            addr = d.order.address
            orders_data.append({
                'id': d.id,
                'earnings': str(d.rider_earning or "0"),
                'accept_url': reverse('accept_order', args=[d.id]),
                'items': [{'name': i.product.name.upper(), 'qty': i.quantity} for i in d.order.items.all()],
                'pickup': {'hub_name': d.nearest_hub.name.upper() if d.nearest_hub else "HUB"},
                'drop': {
                    'full_address': f"{addr.address_line or ''}, {addr.city or ''}".strip(", ") if addr else "Local",
                    'landmark': addr.landmark if addr else ""
                }
            })

    # --- PART C: STATS ---
    # Query performance based on the specific target date
    history_qs = Delivery.objects.filter(delivery_boy=request.user)
    
    # We use assigned_at or delivered_at depending on your workflow; 
    # using delivered_at for earnings is more accurate for payroll.
    delivered_today = history_qs.filter(
        status=DeliveryStatus.DELIVERED,
        delivered_at__range=(start_of_day, end_of_day)
    )

    day_earnings = delivered_today.aggregate(total=Sum('rider_earning'))['total'] or 0
    day_cash = delivered_today.filter(cod_collected=True).aggregate(total=Sum('order__total'))['total'] or 0

    return JsonResponse({
        'assigned': assigned_data,
        'out_deliveries': out_data,
        'orders': orders_data,
        'today_earnings': float(day_earnings),
        'orders_delivered': delivered_today.count(),
        'orders_cancelled': history_qs.filter(
            status=DeliveryStatus.CANCELLED,
            last_location_update__range=(start_of_day, end_of_day)
        ).count(),
        'cash_to_pay': float(day_cash),
        'selected_date': target_date.isoformat(),
        'is_online': profile.is_online
    })

@login_required
@delivery_boy_required
def live_route(request, delivery_id):
    """
    The Shared Map View: 
    This is the 'Core' map that the Rider sees after swiping, 
    and the Customer sees when tracking.
    """
    # Fetch the delivery and ensure the rider is the one assigned
    delivery = get_object_or_404(
        Delivery.objects.select_related('order', 'order__address'), 
        pk=delivery_id, 
        delivery_boy=request.user
    )
    
    # We pass 'is_rider' so the template knows to show Rider-specific 
    # controls (like the 'Complete Delivery' button) vs Customer view.
    context = {
        'delivery': delivery,
        'is_rider': True,
        'customer_lat': delivery.order.address.latitude,
        'customer_lng': delivery.order.address.longitude,
    }
    
    return render(request, 'delivery_portal/live_route.html', context)

def get_delivery_location(request, delivery_id):
    """
    The AJAX 'Core' Sync:
    The Map (Rider/Customer) calls this every few seconds to 
    move the bike icon without refreshing the page.
    """
    delivery = get_object_or_404(Delivery, id=delivery_id)
    return JsonResponse({
        'lat': float(delivery.current_lat) if delivery.current_lat else 0.0,
        'lng': float(delivery.current_lng) if delivery.current_lng else 0.0,
        'status': delivery.status
    })

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt # Or use your CSRF protection logic
def update_rider_location(request, delivery_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        # Save the live coordinates
        delivery.current_lat = data.get('latitude')
        delivery.current_lng = data.get('longitude')
        delivery.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)


