from django.urls import path
from .import views
from admin_dashboard import banner,hub_partner_views,seller_application_views,marketplace_views

urlpatterns = [
    path('',views.dashboard,name='admin_dashboard'),


    path('admin/roles/', views.manage_groups, name='manage_groups'),
    path('admin/roles/edit/<int:pk>/', views.edit_group_permissions, name='edit_group_permissions'),
    path('admin/roles/delete/<int:pk>/', views.delete_group, name='delete_group'),
    path('admin/roles/create/', views.create_custom_group, name='create_custom_group'), 
    path('admin/roles/edit/<int:pk>/', views.edit_group, name='edit_group'),    
   
   
   # admin_dashboard/urls.py
    path('admin/roles/assign/<int:group_id>/', views.assign_group_to_users, name='assign_group_to_users'),
    path('company-info/',views.company_info_update, name='company_info_update'),


    # Banner management
    path('banners/',banner.banner_list,name='banner_list'),
    path('banners/create/',banner.banner_create,name='banner_create'),
    path('banners/<int:pk>/edit/',banner.banner_edit,name='banner_edit'),
    path('banners/<int:pk>/delete/',banner.banner_delete,name='banner_delete'),
    path('banners/<int:pk>/toggle/',banner.banner_toggle,name='banner_toggle'),
    path('banners/<int:pk>/duplicate/',banner.banner_duplicate,name='banner_duplicate'),

    # ── click tracking (public) ────────────────────
    path('b/<int:pk>/click/',banner.banner_click,name='banner_click'),

    #categores section
    path('add_category/',views.add_category,name='add_category'),
    path('edit_category/<int:id>/,',views.edit_category,name='edit_category'),
    path('list_category/',views.list_category,name='list_category'),
    path('delete_category/<int:id>/',views.delete_category,name='delete_category'),

    path('add_product/',views.add_product,name='add_product'),
    path('list_product/',views.list_product,name='list_product'),
    path('edit_product/<slug:slug>/', views.edit_product, name='edit_product'),
    path('delete_product/<slug:slug>/', views.delete_product, name='delete_product'),
    # path('duplicate_product/<slug:slug>/', views.duplicate_product, name='duplicate_product'),
    
    path('hubs/', views.list_delivery_hubs, name='list_delivery_hubs'),
    path('hubs/add/', views.add_delivery_hub, name='add_delivery_hub'),
    path('hubs/edit/<int:pk>/', views.edit_delivery_hub, name='edit_delivery_hub'),
    path('hubs/delete/<int:pk>/', views.delete_delivery_hub, name='delete_delivery_hub'),

    path("inventory/assign/", views.inventory_assign, name="inventory_assign"),

    path('shipping-costs/', views.shipping_cost_list, name='shipping_cost_list'),
    path('shipping-costs/add/', views.add_shipping_cost, name='add_shipping_cost'),
    path('shipping-costs/update/<int:id>/', views.update_shipping_cost, name='update_shipping_cost'),
    path('shipping-costs/delete/<int:id>/', views.delete_shipping_cost, name='delete_shipping_cost'),
 
    # path('check-delivery/', views.check_pincode_delivery, name='check_delivery'),

    path('payment-methods/', views.payment_methods_list, name='payment_methods_list'),
    path('payment-methods/add/', views.payment_method_add, name='payment_method_add'),
    path('payment-methods/<int:pk>/edit/', views.payment_method_edit, name='payment_method_edit'),
    path('payment-methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),

    # Order Management
    path('orders/', views.live_orders_admin, name='admin_orders'),
   path('orders/json/<str:order_number>/', views.admin_order_detail_json,name='admin_order_detail_json'),

    path('orders/json/', views.admin_order_list_json, name='admin_orders_json'),
    path('orders/json/<str:order_number>/', views.admin_order_list_json, name='admin_order_detail_json'),

    
    path('orders/pack/<str:order_number>/', views.mark_order_as_packed, name='mark_as_packed'),
    # ------------------------------------

    path('orders/assign/', views.assign_rider_ajax, name='assign_delivery_ajax'),
    path('orders/reject/', views.reject_order_ajax, name='reject_order_ajax'),
    path('orders/update-status/', views.assign_rider_ajax, name='update_order_status_ajax'),
    path('orders/print/<str:order_number>/', views.order_print_view, name='order_print'),

    path('order/invoice/<int:order_id>/', views.generate_invoice_pdf, name='generate_invoice'),

    #Live inventory
    # path('inventory/restock/<int:product_id>/', views.restock_product, name='restock_product'),
    path('inventory/update-min-stock/<int:product_id>/', views.update_min_stock, name='update_min_stock'),
    
    #Registered customers list
    path('admin-dashboard/customers/', views.admin_customer_list, name='admin_customer_list'),
    path('customers/<int:user_id>/', views.admin_customer_detail, name='customer_detail'),

    # ADMIN: Settlement Dashboard
    path('admin/settlements/', views.rider_cash_settlement_list, name='rider_cash_settlement_list'),
    
    # ADMIN: Actions to clear debt
    path('admin/settle-rider/<int:wallet_id>/', views.settle_rider_handover, name='settle_rider_handover'),



    path('shops/', views.shop_list, name='shop_list'),

    path('shops/add/', views.add_shop, name='add_shop'),

    path('shops/<int:pk>/edit/', views.edit_shop, name='edit_shop'),

    path('shops/<int:pk>/delete/', views.delete_shop, name='delete_shop'),

    #======================================================

    path("hub-partners/",hub_partner_views.hub_partner_list,name="hub_partner_list"),

    path("hub-partners/add/",hub_partner_views.add_hub_partner,name="add_hub_partner"),

    path("hub-partners/<int:partner_id>/edit/",hub_partner_views.edit_hub_partner,name="edit_hub_partner"),

    path("hub-partners/<int:partner_id>/toggle-status/",hub_partner_views.toggle_hub_partner_status,name="toggle_hub_partner_status"),

    path("hub-partners/<int:partner_id>/",hub_partner_views.hub_partner_detail,name="hub_partner_detail"),



    path("sell-on-gramacart/",seller_application_views.seller_application,name="seller_application"),
    path('sell-on-gramacart/success/',seller_application_views.seller_success,name='seller_success'),
    path("seller-applications/",seller_application_views.seller_application_list,name="seller_application_list"),
    path("seller-applications/<int:pk>/",seller_application_views.seller_application_detail,name="seller_application_detail"),

    path("seller-applications/<int:pk>/approve/",seller_application_views.approve_seller_application,name="approve_seller_application"),

    path("seller-applications/<int:pk>/reject/",seller_application_views.reject_seller_application,name="reject_seller_application"),

    path(
        "catalogue/<int:hub_id>/",
        views.generate_catalogue,
        name="generate_catalogue",
    ),


    path(
        "marketplace-settings/",
        marketplace_views.marketplace_settings,
        name="marketplace_settings",
    ),
]

