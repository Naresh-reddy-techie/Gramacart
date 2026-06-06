from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User, Group
from .forms import DeliveryBoyUpdateForm
from .models import Delivery, DeliveryProfile, DeliveryStatus
from shop.models import Order
from django.utils import timezone
import traceback
from django.db import transaction


def delivery_boy_required(view_func):
    """Ensures only members of the 'DeliveryBoy' group can access rider views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name='DeliveryBoy').exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access restricted to Delivery Partners.")
        return redirect('login')
    return wrapper




from django.utils.timezone import localdate, make_aware
import datetime as dt_module  # Use an alias to prevent clashes
from datetime import timedelta
from itertools import groupby

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
        status=DeliveryStatus.OUT_FOR_DELIVERY
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
    
    profile = DeliveryProfile.objects.select_related('hub','user').get(user=request.user)
    
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


from payments.logic import settle_order_funds # Import our logic
@login_required
@delivery_boy_required
def update_status_api(request):
    
    data = json.loads(request.body)
    order_num = data.get('order_number')

    new_status = data.get('status')
    allowed_statuses = [
        DeliveryStatus.ASSIGNED,
        DeliveryStatus.OUT,
        DeliveryStatus.DELIVERED,
        DeliveryStatus.CANCELLED,
    ]
    
    delivery = Delivery.objects.get(order__order_number=order_num)
    delivery.status = new_status
    delivery.save(update_fields=[
        'status',
        'delivered_at'
    ])

    # CRITICAL: Trigger the Money Splitter when delivered
    if new_status not in allowed_statuses:
        return JsonResponse({'success': 'error','message':'Invalide status'},status=400)



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


def update_rider_location(request, delivery_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        delivery = get_object_or_404(Delivery, id=delivery_id,delivery_boy=request.user)
        
        # Save the live coordinates
        delivery.current_lat = data.get('latitude')
        delivery.current_lng = data.get('longitude')
        delivery.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)


