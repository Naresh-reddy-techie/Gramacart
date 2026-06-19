
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='homepage'),
    path('user_signup/',views.user_signup,name='user_signup'),
    path('user_signin/',views.user_signin,name='user_signin'),
    path('user_logout/',views.user_logout,name='user_logout'),

    path("auth/request-otp/", views.request_otp, name="request_otp"),
    path("auth/verify-otp/", views.verify_otp, name="verify_otp"),

    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]

