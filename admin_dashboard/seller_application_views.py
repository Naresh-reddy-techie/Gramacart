from django.shortcuts import render, redirect

from admin_dashboard.models import SellerApplication,Shop
from admin_dashboard.forms import SellerApplicationForm


def seller_application(request):

    if request.method == "POST":

        form = SellerApplicationForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('seller_success')

    else:

        form = SellerApplicationForm()

    return render(
        request,
        'seller_application/seller_form.html',
        {'form': form}
    )


def seller_success(request):

    return render(
        request,
        'seller_application/seller_success.html'
    )

from django.shortcuts import render, get_object_or_404

from admin_dashboard.models import SellerApplication


def seller_application_list(request):

    applications = SellerApplication.objects.order_by(
        '-created_at'
    )

    context = {
        "applications": applications
    }

    return render(
        request,
        "seller_application/seller_application_list.html",
        context
    )


def seller_application_detail(request, pk):

    application = get_object_or_404(
        SellerApplication,
        pk=pk
    )

    context = {
        "application": application
    }

    return render(
        request,
        "seller_application/seller_application_detail.html",
        context
    )


def approve_seller_application(request, pk):

    application = get_object_or_404(
        SellerApplication,
        pk=pk
    )

    if application.status != 'APPROVED':

        application.status = 'APPROVED'
        application.save()

        Shop.objects.create(

            seller_application=application,

            name=application.business_name,

            shop_type='KIRANA',

            hub=application.hub,

            phone=application.phone,

            is_internal=False

        )

        messages.success(
            request,
            "Seller approved successfully."
        )

    return redirect(
        'seller_application_detail',
        pk=application.pk
    )


def reject_seller_application(request, pk):

    application = get_object_or_404(
        SellerApplication,
        pk=pk
    )

    application.status = 'REJECTED'
    application.save()

    messages.success(
        request,
        "Seller application rejected."
    )

    return redirect(
        'seller_application_detail',
        pk=application.pk
    )