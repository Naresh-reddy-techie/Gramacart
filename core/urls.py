from django.urls import path
from core.views import post_login_redirect

urlpatterns = [
    path("redirect/", post_login_redirect, name="post_login_redirect"),
]