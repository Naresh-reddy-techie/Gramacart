
from django.contrib import admin
from django.urls import path,include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Homepage.urls')),
    path('accounts/',include('accounts.urls')),
    path('admin_dashboard/',include('admin_dashboard.urls')),
    path('shop/',include('shop.urls')),
    path('payment/',include('payments.urls')),
    path('delivery_portal/',include('delivery_portal.urls')),
   
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)