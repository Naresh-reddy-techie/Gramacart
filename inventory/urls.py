from django.urls import path
from .import views 

urlpatterns = [
    path('inventory/live/', views.live_inventory, name='live_inventory'),

    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.add_inventory, name='add_inventory'),
    path('inventory/edit/<int:pk>/', views.edit_inventory, name='edit_inventory'),
    path('inventory/delete/<int:pk>/', views.delete_inventory, name='delete_inventory'),
    path('inventory/update-stock/<int:pk>/',views. update_stock, name='update_stock'),
]