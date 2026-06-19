
from django.urls import path

from delivery_portal import (
    views,
    auth_views,
    rider_views,
    admin_views,
    api_views,
)

urlpatterns = [

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    path(
        'login/',
        auth_views.login_user,
        name='delivery_login'
    ),

    path(
        'logout/',
        auth_views.logout_view,
        name='delivery_logout'
    ),

    # =========================================================
    # RIDER DASHBOARD
    # =========================================================

    path(
        'rider/dashboard/',
        rider_views.dashboard,
        name='rider_dashboard'
    ),
    path(
        "rider/dashboard/api/",
        rider_views.dashboard_api,
        name="dashboard_api"
    ),
    # =========================================================
    # DELIVERY OPERATIONS
    # =========================================================

    path(
        'delivery/accept/<int:delivery_id>/',
        rider_views.accept_order,
        name='accept_order'
    ),

    path(
        'delivery/pickup/<int:delivery_id>/',
        rider_views.confirm_pickup,
        name='delivery_pickup'
    ),

    path(
        'rider/complete/<int:delivery_id>/',
        rider_views.complete_delivery,
        name='complete_delivery'
    ),


    # =========================================================
    # RIDER FEATURES
    # =========================================================

    path(
        'rider/active/',
        views.rider_active_deliveries,
        name='active_deliveries'
    ),

    path(
        'rider/earnings/',
        views.rider_earnings,
        name='rider_earnings'
    ),

    path(
        'rider/profile/',
        views.rider_profile,
        name='rider_profile'
    ),

    # =========================================================
    # LIVE ROUTE & TRACKING
    # =========================================================

    path(
        'rider/live-route/<int:delivery_id>/',
        views.live_route,
        name='live_route'
    ),

    path(
        'api/delivery-location/<int:delivery_id>/',
       views.get_delivery_location,
        name='get_delivery_location'
    ),

    path(
        'rider/location/update/<int:delivery_id>/',
        api_views.update_rider_location,
        name='update_rider_location'
    ),

    # =========================================================
    # DUTY & LIVE ORDER RADAR
    # =========================================================

    path(
        'toggle-duty/',
        api_views.toggle_duty,
        name='toggle_duty'
    ),

    path(
        'check-new-orders/',
        api_views.check_new_orders,
        name='check_new_orders'
    ),

    # =========================================================
    # DELIVERY STATUS APIs
    # =========================================================

    path(
        'api/update-status/',
        views.update_delivery_status,
        name='update_status_api'
    ),

    # =========================================================
    # ADMIN DELIVERY MANAGEMENT
    # =========================================================

    path(
        'admin/deliveries/',
        admin_views.admin_delivery_list,
        name='admin_delivery_list'
    ),

    path(
        'admin/delivery/create/<int:order_id>/',
       views.create_delivery_from_order,
        name='create_delivery_from_order'
    ),

    path(
        'admin/delivery/assign/<int:delivery_id>/',
        admin_views.manual_assign_delivery,
        name='manual_assign_delivery'
    ),

    # =========================================================
    # DELIVERY PARTNER MANAGEMENT
    # =========================================================

    path(
        'admin/partners/',
        admin_views.list_delivery_boys,
        name='delivery_boy_list'
    ),

    path(
        'admin/partners/add/',
        admin_views.add_delivery_boy,
        name='add_delivery_boy'
    ),

    path(
        'admin/partners/add/success/',
        views.onboarding_success,
        name='onboarding_success'
    ),

    path(
        'admin/partners/update/<int:user_id>/',
        views.update_delivery_boy,
        name='update_delivery_boy'
    ),

    path(
        'admin/partners/delete/<int:profile_id>/',
        views.delete_delivery_boy,
        name='delete_delivery_boy'
    ),
]

