from django.urls import path
from .import views ,shipping_cost_views

urlpatterns = [
    path('hub_dashboard/',views.hub_dashboard,name='hub_dashboard'),
    path("orders/", views.hub_orders, name="hub_orders"),
    path("orders/json/",views.hub_orders_json,name = "hub_orders_json"),
    # Shipping Cost
    path("shipping-cost/",shipping_cost_views.shipping_cost_list,name="hub_shipping_cost_list"),

    path("shipping-cost/add/",shipping_cost_views.add_shipping_cost,name="hub_add_shipping_cost"),

    path("shipping-cost/edit/<int:pk>/",shipping_cost_views.edit_shipping_cost,name="hub_edit_shipping_cost"),

    path("shipping-cost/delete/<int:pk>/",shipping_cost_views.delete_shipping_cost,name="hub_delete_shipping_cost"),
]