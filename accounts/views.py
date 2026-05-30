
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


def user_signin(request):

    if request.method == "POST":

        form = LoginForm(request, data=request.POST)

        if form.is_valid():

            user = form.get_user()

            if not user.is_active:
                messages.error(request, "Your account is inactive.")
                return redirect("signin")

            login(request, user)

            messages.success(request, "Successfully signed in.")

            # Role based redirect
            if user.is_superuser:
                return redirect("dashboard")

            elif user.groups.filter(name="DeliveryBoy").exists():
                return redirect("rider_dashboard")

            else:
                return redirect("where_we_deliver")

        else:
            messages.error(request, "Invalid username or password.")

    else:
        form = LoginForm()

    return render(request, "accounts/signin.html", {"form": form})


from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

@require_POST  # Security: Only allows logout via a POST request (form submission)
def user_logout(request):
    logout(request)
    # Adding a message lets the user know the session is officially closed
    messages.success(request, "You have been successfully logged out from GramaCart.")
    return redirect('home')

