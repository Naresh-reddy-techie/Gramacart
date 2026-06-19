
#This is for email authentication 

from django.shortcuts import render,redirect
from django.contrib.auth.models import auth
from .forms import CreateUserForm,LoginForm
from django.contrib.auth import authenticate,logout,login
from django.contrib.auth.decorators import login_required 
from django.contrib import messages  


def home(request):
    return render(request, 'homepage.html')


def user_signup(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Account created Succesfully Please Log in to your Account")
            return redirect('user_signin')
      
    else:
        form = CreateUserForm()
    context = {'signupform':form}
    return render(request,'accounts/signup.html',context)




from django.utils.http import url_has_allowed_host_and_scheme

def user_signin(request):

    if request.method == "POST":

        form = LoginForm(request, data=request.POST)

        if form.is_valid():

            user = form.get_user()

            if not user.is_active:
                messages.error(request, "Your account is inactive.")
                return redirect("user_signin")

            login(request, user)

            messages.success(request, "Successfully signed in.")

            # =================================================
            # 🔥 FIX: RESUME FLOW (IMPORTANT)
            # =================================================
            next_url = request.GET.get("next")

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            # fallback
            return redirect(get_dashboard_url(user))

        messages.error(request, "Invalid username or password.")

    else:
        form = LoginForm()

    return render(request, "accounts/signin.html", {"form": form})

"""
from core.role_router import get_dashboard_url

def user_signin(request):

    if request.method == "POST":

        form = LoginForm(request, data=request.POST)

        if form.is_valid():

            user = form.get_user()

            if not user.is_active:
                messages.error(request,"Your account is inactive.")
                return redirect("user_signin")

            login(request, user)

            messages.success(request,"Successfully signed in.")

            return redirect(get_dashboard_url(user))

        else:

            messages.error(
                request,
                "Invalid username or password."
            )

    else:
        form = LoginForm()

    return render(
        request,
        "accounts/signin.html",
        {"form": form}
    )

    
"""

from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST



@require_POST
def user_logout(request):

    print("========== USER LOGOUT EXECUTED ==========")

    logout(request)

    messages.success(
        request,
        "You have been successfully logged out from GramaCart."
    )

    return redirect('homepage')

import random

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User

from core.role_router import get_dashboard_url

def request_otp(request):
    """
    Step 1:
    User enters mobile number.
    System generates OTP and stores it in session.
    """

   
    if request.method == "POST":

        phone = request.POST.get("phone", "").strip()

        # --------------------------------------------------
        # Basic Mobile Validation
        # --------------------------------------------------
        if (
            not phone
            or len(phone) != 10
            or not phone.isdigit()
            or phone[0] not in "6789"
        ):
            messages.error(
                request,
                "Please enter a valid 10-digit mobile number."
            )
            return redirect("request_otp")

        # --------------------------------------------------
        # Generate OTP
        # --------------------------------------------------
        otp = f"{random.randint(1000, 9999)}"

        # --------------------------------------------------
        # Store in Session
        # --------------------------------------------------
        request.session["otp"] = otp
        request.session["phone"] = phone

        # --------------------------------------------------
        # Debug Only (Remove when SMS is integrated)
        # --------------------------------------------------
        print("\n" + "=" * 60)
        print(f"GRAMACART OTP FOR {phone} : {otp}")
        print("=" * 60 + "\n")

        next_url = request.GET.get("next")

        if next_url:
            request.session["next_url"] = next_url

        return redirect("verify_otp")

    return render(
        request,
        "accounts/request_otp.html"
    )


from shop.models import CustomerProfile

def verify_otp(request):

    if request.method == "POST":

        input_otp = request.POST.get("otp")

        if input_otp == request.session.get("otp"):

            phone = request.session.get("phone")

            user, created = User.objects.get_or_create(
                username=phone
            )

            if created:
                user.set_unusable_password()
                user.save()

            # Create customer profile automatically
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": phone
                }
            )

            login(request, user)

            messages.success(
                request,
                "Welcome to GramaCart"
            )

            next_url = request.session.pop(
                "next_url",
                None
            )

            if next_url:

                # Never redirect back to POST endpoints
                if "/shop/cart/add/" in next_url:

                    return redirect("public_dashboard")

                return redirect(next_url)


            return redirect(
                get_dashboard_url(user)
            )

        messages.error(
            request,
            "Invalid OTP"
        )

    return render(
        request,
        "accounts/verify_otp.html",
        {
            "demo_otp": request.session.get("otp")
        }
    )
