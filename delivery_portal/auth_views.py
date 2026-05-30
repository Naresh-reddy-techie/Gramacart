from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


# ------------------- AUTHENTICATION -------------------

def login_user(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='DeliveryBoy').exists():
            return redirect('rider_dashboard')
        return redirect('user_signup')

    if request.method == "POST":
        u_name = request.POST.get("username")
        p_word = request.POST.get("password")
        user = authenticate(request, username=u_name, password=p_word)
        
        if user:
            login(request, user)
            if user.groups.filter(name='DeliveryBoy').exists():
                return redirect('rider_dashboard')
            return redirect('admin_delivery_list')
        messages.error(request, "Invalid username or password.")
            
    return redirect('user_signin')

def logout_view(request):
    logout(request)
    return redirect('login')