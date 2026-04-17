from django.views.generic import TemplateView
from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('sw.js', (TemplateView.as_view(template_name="sw.js", content_type='application/javascript',)), name='sw.js'),
]