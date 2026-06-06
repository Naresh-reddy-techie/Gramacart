from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from core.roles import (
    is_admin,
    is_hub_partner,
    is_delivery_boy,
)

from core.role_router import get_dashboard_url


def role_required(role_check_func):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect("user_signin")

            if not role_check_func(request.user):

                messages.error(
                    request,
                    "You are not authorized to access this page."
                )

                return redirect(
                    get_dashboard_url(request.user)
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    return role_required(is_admin)(view_func)


def hub_partner_required(view_func):
    return role_required(is_hub_partner)(view_func)


def delivery_boy_required(view_func):
    return role_required(is_delivery_boy)(view_func)