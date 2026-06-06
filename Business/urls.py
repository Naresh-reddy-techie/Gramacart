
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
    path('inventory/', include('inventory.urls')),
    path('core/',include('core.urls')),
    path('hub_partner/',include('hub_partner.urls')),
   
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)

"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import set_language, i18n_patterns

urlpatterns = [
    path('i18n/setlang/', set_language, name='set_language'),
    path('admin/', admin.site.urls),
]

urlpatterns += i18n_patterns(
    path('', include('Homepage.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin_dashboard/', include('admin_dashboard.urls')),
    path('shop/', include('shop.urls')),
    path('payment/', include('payments.urls')),
    path('delivery_portal/', include('delivery_portal.urls')),
    path('inventory/', include('inventory.urls'))
)

# ✅ THIS PART IS CRITICAL
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

"""