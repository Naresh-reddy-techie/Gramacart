from .models import Delivery,DeliveryProfile,DeliveryStatus
from admin_dashboard.models import DeliveryHub
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.db import transaction
from django.contrib.auth.models import User, Group
from .forms import ManualAssignForm
from django.utils import timezone
# -------------------  ADMIN: FLEET & OPERATIONS -------------------

@login_required
def list_delivery_boys(request):
    """List all partners and their current availability."""
    profiles = DeliveryProfile.objects.select_related('user', 'hub').all()
    busy_ids = Delivery.objects.filter(
        status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.OUT_FOR_DELIVERY]
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