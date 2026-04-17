from django.urls import path
from .import views


urlpatterns = [
    path('',views.dashboard,name='dashboard'),
    path('admin/roles/', views.manage_groups, name='manage_groups'),
    path('admin/roles/edit/<int:pk>/', views.edit_group_permissions, name='edit_group_permissions'),
    path('admin/roles/delete/<int:pk>/', views.delete_group, name='delete_group'),
    path('admin/roles/create/', views.create_custom_group, name='create_custom_group'), 
    path('admin/roles/edit/<int:pk>/', views.edit_group, name='edit_group'),    
   
   
   # admin_dashboard/urls.py
    path('admin/roles/assign/<int:group_id>/', views.assign_group_to_users, name='assign_group_to_users'),
    path('company-info/',views.company_info_update, name='company_info_update'),


    path('add_category/',views.add_category,name='add_category'),
    path('edit_category/<int:id>/,',views.edit_category,name='edit_category'),
    path('list_category/',views.list_category,name='list_category'),
    path('delete_category/<int:id>/',views.delete_category,name='delete_category'),

    path('add_product/',views.add_product,name='add_product'),
    path('list_product/',views.list_product,name='list_product'),
    path('edit_product/<slug:slug>/', views.edit_product, name='edit_product'),
    path('delete_product/<slug:slug>/', views.delete_product, name='delete_product'),
    path('duplicate_product/<slug:slug>/', views.duplicate_product, name='duplicate_product'),
    
    path('hubs/', views.list_delivery_hubs, name='list_delivery_hubs'),
    path('hubs/add/', views.add_delivery_hub, name='add_delivery_hub'),
    path('hubs/edit/<int:pk>/', views.edit_delivery_hub, name='edit_delivery_hub'),
    path('hubs/delete/<int:pk>/', views.delete_delivery_hub, name='delete_delivery_hub'),

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
    path('orders/json/', views.admin_order_list_json, name='admin_orders_json'),
    path('orders/json/<str:order_number>/', views.admin_order_list_json, name='admin_order_detail_json'),

    # --- ADD THIS LINE TO FIX THE 404 ---
    path('orders/pack/<str:order_number>/', views.mark_order_as_packed, name='mark_as_packed'),
    # ------------------------------------

    path('orders/assign/', views.update_order_status_ajax, name='assign_delivery_ajax'),
    path('orders/reject/', views.reject_order_ajax, name='reject_order_ajax'),
    path('orders/update-status/', views.update_order_status_ajax, name='update_order_status_ajax'),
    path('orders/print/<str:order_number>/', views.order_print_view, name='order_print'),

    path('order/invoice/<int:order_id>/', views.generate_invoice_pdf, name='generate_invoice'),

    #Live inventory
    path('inventory/live/', views.live_inventory, name='live_inventory'),
    path('inventory/restock/<int:product_id>/', views.restock_product, name='restock_product'),
    path('inventory/update-min-stock/<int:product_id>/', views.update_min_stock, name='update_min_stock'),
    
    #Registered customers list
    path('admin-dashboard/customers/', views.admin_customer_list, name='admin_customer_list'),
    path('customers/<int:user_id>/', views.admin_customer_detail, name='customer_detail'),

    # ADMIN: Settlement Dashboard
    path('admin/settlements/', views.rider_cash_settlement_list, name='rider_cash_settlement_list'),
    
    # ADMIN: Actions to clear debt
    path('admin/settle-rider/<int:wallet_id>/', views.settle_rider_handover, name='settle_rider_handover'),
    
]

