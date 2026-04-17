from django.urls import path
from . import views

urlpatterns = [
    # -------------------
    # Authentication
    # -------------------
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # -------------------
    # Rider / Delivery Partner Portal
    # -------------------
    path('rider/dashboard/', views.dashboard, name='rider_dashboard'),
    
    # NEW: Self-Acceptance Logic
    path('delivery/accept/<int:delivery_id>/', views.accept_order, name='accept_order'),    
    # Delivery Actions
    path('delivery/pickup/<int:delivery_id>/', views.confirm_pickup, name='delivery_pickup'),
    path('rider/complete/<int:delivery_id>/', views.complete_delivery, name='delivery_complete'),
    path('rider/failed/<int:delivery_id>/', views.delivery_failed, name='delivery_cancel'),
    
    # Tracking & Stats
    path('rider/active/', views.rider_active_deliveries, name='active_deliveries'),
    path('rider/earnings/', views.rider_earnings, name='rider_earnings'),
    path('rider/profile/', views.rider_profile, name='rider_profile'),
    
    # --- FIXED: THE CORE MAP LINK ---
    # This serves the live map that both Rider and Customer will use
    path('rider/live-route/<int:delivery_id>/', views.live_route, name='live_route'),
    
   
    # --- Market & Duty Logic (AJAX Endpoints) ---
    path('toggle-duty/', views.toggle_duty, name='toggle_duty'),
    path('check-new-orders/', views.check_new_orders, name='check_new_orders'),
    
    # Location & Status Updates
    path('rider/location/update/<int:delivery_id>/', views.update_rider_location, name='update_rider_location'),
    path('api/update-status/', views.update_delivery_status, name='update_status_api'),
    # FIXED: API for the map to fetch coordinates without refreshing
    path('api/delivery-location/<int:delivery_id>/', views.get_delivery_location, name='get_delivery_location'),

    # -------------------
    # Admin / Operations Management
    # -------------------
    path('admin/deliveries/', views.admin_delivery_list, name='admin_delivery_list'),
    path('admin/delivery/create/<int:order_id>/', views.create_delivery_from_order, name='create_delivery_from_order'),
    path('admin/delivery/assign/<int:delivery_id>/', views.manual_assign_delivery, name='manual_assign_delivery'),

    # Partner Management (CRUD)
    path('admin/partners/', views.list_delivery_boys, name='delivery_boy_list'),
    path('admin/partners/add/', views.add_delivery_boy, name='add_delivery_boy'),
    path('admin/partners/add/success/', views.onboarding_success, name='onboarding_success'),
    path('admin/partners/update/<int:user_id>/', views.update_delivery_boy, name='update_delivery_boy'),
    path('admin/partners/delete/<int:profile_id>/', views.delete_delivery_boy, name='delete_delivery_boy'),
]