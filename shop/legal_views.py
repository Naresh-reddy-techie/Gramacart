from django.shortcuts import render

#---------------------------------------------------
#   For CUSTOMERS
#---------------------------------------------------

def terms_conditions(request):
    return render(request, "legal/terms_conditions.html")

def privacy_policy(request):
    return render(request, "legal/privacy_policy.html")

def refund_cancellation_policy(request):
    return render(request,"legal/refund_cancellation_policy.html")

def delivery_policy(request):
    return render(request,"legal/delivery_policy.html")


#---------------------------------------------------
#   For SELLERS
#---------------------------------------------------

def seller_terms(request):
    return render(request,"legal/seller_terms.html")


def seller_commission_policy(request):
    return render(request,"legal/seller_commission_policy.html")


def seller_privacy_policy(request):
    return render(request,"legal/seller_privacy_policy.html")