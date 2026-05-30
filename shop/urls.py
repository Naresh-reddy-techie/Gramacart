from django.urls import path
from .import views

urlpatterns = [

    path( 'where-we-deliver/', views.where_should_we_deliver, name='where_we_deliver' ), 
    path( 'check-delivery-availability/', views.check_delivery_availability, name='check_delivery_availability' ),


    # 1. Dashboards & Profiles
    path('public_dashboard/', views.public_dashboard, name='public_dashboard'),
    path('category/<slug:category_slug>/', views.public_dashboard, name='public_dashboard_by_category'), 
    path('manage_profile/', views.manage_profile, name='manage_profile'),
    path('profile_view/', views.profile_view, name='profile_view'),  
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # 2. Addresses
    path('addresses/', views.address_list, name='address_list'), # Moved from '' to 'addresses/' to avoid clashes
    path('addresses/create/', views.address_form, name='address_create'),
    path('addresses/update/<int:pk>/', views.address_form, name='address_update'),
    path('addresses/delete/<int:pk>/', views.address_delete, name='address_delete'),
    # path('reverse-geocode/', views.reverse_geocode, name='reverse_geocode'),
    
    # 3. Cart & Checkout (ALIGNED WITH JAVASCRIPT)
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update_cart_quantity/<int:cart_item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart_checkout/', views.cart_checkout, name='cart_checkout'),
    path('get_shipping_cost/', views.get_shipping_cost, name='get_shipping_cost'),
    
    # 4. Wishlist & Buy Now
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('buy-now-shipping/<int:product_id>/', views.get_buy_now_shipping_cost, name='get_buy_now_shipping_cost'),

    # 5. Orders & Tracking
    path('orders/', views.order_list, name='orders_list'),
    path('orders/<int:order_id>/details/', views.order_detail, name='order_detail'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/track/<int:order_id>/', views.track_order, name='track_order'),
    path('api/order/status/<int:order_id>/', views.get_order_status_json, name='order_status_api'),
    path('product/<int:id>/rate/', views.rate_product, name='rate_product')]