from django.urls import path
from .import views,legal_views

urlpatterns = [

    path( 'where-we-deliver/', views.where_should_we_deliver, name='where_we_deliver' ), 
    path( 'check-delivery-availability/', views.check_delivery_availability, name='check_delivery_availability' ),
    
    # urls.py
    path("smtp-test/",views.smtp_test,name='smtp_test'),
    # 1. Dashboards & Profiles
    path('public_dashboard/', views.public_dashboard, name='public_dashboard'),
    path('category/<slug:category_slug>/', views.public_dashboard, name='public_dashboard_by_category'), 
    path('manage_profile/', views.manage_profile, name='manage_profile'),
    path('profile_view/', views.profile_view, name='profile_view'),  
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path("catalog-version/",views.catalog_version,name="catalog_version"),

    # 2. Addresses
    path('addresses/', views.address_list, name='address_list'), # Moved from '' to 'addresses/' to avoid clashes
    path('addresses/create/', views.address_form, name='address_create'),
    path('addresses/update/<int:pk>/', views.address_form, name='address_update'),
    path('addresses/delete/<int:pk>/', views.address_delete, name='address_delete'),
    # path('reverse-geocode/', views.reverse_geocode, name='reverse_geocode'),

    path("rate/<int:id>/",views.rate_product,name="rate_product"),
    path("orders/<int:order_id>/track/",views.track_order,name="track_order"),
    
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
    path('product/<int:id>/rate/', views.rate_product, name='rate_product'),
    
    #6 . legal policy for customers
    path( "terms-and-conditions/",legal_views.terms_conditions,name="terms_conditions"),
    path("privacy-policy/",legal_views.privacy_policy,name="privacy_policy"),
    path("refund-cancellation-policy/",legal_views.refund_cancellation_policy,name="refund_cancellation_policy"),
    path("delivery-policy/",legal_views.delivery_policy,name="delivery_policy"),

    #7 . legal policy for sellers
    path("legal/seller-terms/",legal_views.seller_terms,name="seller_terms"),
    path("legal/seller-commission-policy/",legal_views.seller_commission_policy,name="seller_commission_policy"),
    path("legal/seller-privacy-policy/",legal_views.seller_privacy_policy,name="seller_privacy_policy"),
]