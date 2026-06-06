
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from core.role_router import get_dashboard_url


@login_required
def post_login_redirect(request):
    """
    Redirect user to correct dashboard after login.
    """
    return redirect(get_dashboard_url(request.user))