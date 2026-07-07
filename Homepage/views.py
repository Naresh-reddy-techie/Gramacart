from django.shortcuts import render
from django.utils.timezone import now
from admin_dashboard.models import CompanyInfo, Product, DeliveryHub,Category

def homepage(request):
    company_info = CompanyInfo.objects.first()
    # Use the correct related_name from your model
    products = Product.objects.filter(is_active=True).prefetch_related('product_images')
    
    # Safely get hub info
    hub = DeliveryHub.objects.first()

    categories = Category.objects.all()[:8]
    total_categories = Category.objects.count()
    
    context = {
        "site_content": company_info,
        "products": products,
        "year": now().year,
        "name": company_info.name if company_info else "GramaCart",
        "delivery_hub": hub.max_delivery_radius_km if hub else 5,
        "categories": categories,
        "total_categories": total_categories,
    }
    return render(request, "homepage.html", context)



#for free renderaccounts ping for no sleep 
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "GramaCart",
    })