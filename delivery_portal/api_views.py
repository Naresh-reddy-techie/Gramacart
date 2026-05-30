from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db import transaction
import json
from django.http import JsonResponse
from .views import delivery_boy_required
from django.views.decorators.csrf import csrf_exempt
from .models import Delivery,DeliveryStatus
from datetime import datetime
from django.utils import timezone
from django.urls import reverse

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
def check_new_orders(request):

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
        status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.OUT_FOR_DELIVERY]
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

        market_orders = (

            Delivery.objects

            .select_related(
                'order',
                'order__address',
                'nearest_hub'
            )

            .prefetch_related(
                'order__items',
                'order__items__product'
            )

            .filter(

                # Ready for rider pickup
                status=DeliveryStatus.PACKED,

                # Not accepted yet
                delivery_boy__isnull=True,

                # REAL BUSINESS LOGIC
                nearest_hub=profile.hub,

                # Safety checks
                nearest_hub__isnull=False
            )

            .order_by('-created_at')
        )

        print("===================================")
        print("RIDER:", request.user.username)
        print("RIDER HUB:", profile.hub.name)
        print("TOTAL MATCHED:", market_orders.count())
        print("===================================")

        for d in market_orders:

            addr = d.order.address
            hub = d.nearest_hub

            orders_data.append({

                'id': d.id,

                'order_number': d.order.order_number,

                'earnings': str(
                    d.rider_earning or "0"
                ),

                'accept_url': reverse(
                    'accept_order',
                    args=[d.id]
                ),

                'pickup': {

                    'hub_name': (
                        hub.name.upper()
                        if hub else "HUB"
                    )

                },

                'drop': {

                    'full_address': (
                        f"{addr.address_line or ''}, "
                        f"{addr.city or ''}"
                    ).strip(", ") if addr else "Local",

                    'landmark': (
                        addr.landmark
                        if addr else ""
                    )

                },

                'items': [

                    {
                        'name': item.product.name.upper(),
                        'qty': item.quantity
                    }

                    for item in d.order.items.all()

                ]

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
