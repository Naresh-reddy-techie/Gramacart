import urllib.parse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Payment, PaymentMethod
from payments.gateway_factory import get_gateway
from shop.models import Order
from django.contrib.auth.decorators import login_required
import qrcode
import io
import base64

@login_required
def payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    active_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order')

    # Get UPI config
    upi_method = active_methods.filter(name='upi').first()
    upi_config = {}
    upi_uri = ""
    upi_qr_base64 = None

    if upi_method and upi_method.config:
        upi_id = upi_method.config.get('upi_id', '')
        payee_name = upi_method.config.get('payee_name', '')
        upi_config = {
            'upi_id': upi_id,
            'payee_name': payee_name,
        }
        payee_name_encoded = urllib.parse.quote(payee_name)
        upi_uri = f"upi://pay?pa={upi_id}&pn={payee_name_encoded}&am={order.total}&cu=INR"

        # Generate QR code
        qr = qrcode.make(upi_uri)
        buffered = io.BytesIO()
        qr.save(buffered, format="PNG")
        upi_qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    if request.method == 'POST':
        selected_payment_method_name = request.POST.get('payment_method')
        txn_id = request.POST.get('txn_id', '').strip()  # UPI txn ID

        try:
            payment_method = PaymentMethod.objects.get(name=selected_payment_method_name, is_active=True)
        except PaymentMethod.DoesNotExist:
            messages.error(request, "Invalid payment method.")
            return redirect('payment', order_id=order.id)

        # Create payment record
        payment = Payment.objects.create(
            order=order,
            method=payment_method,
            amount=order.total,
            currency='INR',
            status='pending',
        )

        # ✅ UPI Flow (manual confirmation)
        if payment_method.name == 'upi':
            txn_id = request.POST.get('txn_id')

            if not txn_id:
                messages.error(request, "Please enter the UPI transaction ID.")
                return redirect('payment', order_id=order.id)

            # Save UPI txn_id
            payment.transaction_id = txn_id
            payment.status = 'pending'  # still pending until admin verifies
            payment.save()
            messages.success(request,"UPI reference submitted.we'll confirm it soon.")
            # Redirect to confirmation page
            return redirect('order_pending_confirmation', order_id=order.id)

        # 🔁 Other Gateways (Stripe, Razorpay, etc.)
        try:
            gateway = get_gateway(payment_method.name)
            response = gateway.initiate_payment(order, payment_method.config)

            if response['status'] == 'success':
                payment.status = 'success'
                payment.reference_id = response.get('reference_id')
                payment.transaction_id = response.get('transaction_id')
                order.status = 'paid'
                order.save()
                payment.save()
                messages.success(request, "Payment successful!")
                return redirect('order_success', order_id=order.id)

            elif response.get('redirect_url'):
                payment.reference_id = response.get('reference_id')
                payment.save()
                return redirect(response['redirect_url'])

            else:
                payment.status = 'failed'
                payment.error_message = "Unknown error."
                payment.save()
                messages.error(request, "Payment failed.")
                return redirect('payment', order_id=order.id)

        except Exception as e:
            payment.status = 'failed'
            payment.error_message = str(e)
            payment.save()
            messages.error(request, f"Payment error: {e}")
            return redirect('payment', order_id=order.id)

    return render(request, 'payments/payment.html', {
        'order': order,
        'payment_methods': active_methods,
        'upi_config': upi_config,
        'upi_uri': upi_uri,
        'upi_qr_base64': upi_qr_base64,
    })


#=======================================================================

import requests

@login_required
def paypal_success(request):
    token = request.GET.get('token')  # This is PayPal's order ID
    if not token:
        messages.error(request, "Missing PayPal token.")
        return redirect('cart')

    try:
        payment = Payment.objects.get(reference_id=token)
        payment_method = payment.method
        config = payment_method.config

        access_token = requests.post(
            'https://api.sandbox.paypal.com/v1/oauth2/token',
            auth=(config['client_id'], config['client_secret']),
            data={'grant_type': 'client_credentials'}
        ).json()['access_token']

        capture_response = requests.post(
            f"https://api.sandbox.paypal.com/v2/checkout/orders/{token}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )

        capture_data = capture_response.json()
        payment.status = 'success'
        payment.transaction_id = capture_data['purchase_units'][0]['payments']['captures'][0]['id']
        payment.save()

        order = payment.order
        order.status = 'paid'
        order.save()

        messages.success(request, "Payment successful!")
        return render(request, 'payments/paypal_success.html', {'order': order})

    except Payment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('cart')

    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('cart')


@login_required
def paypal_cancel(request):
    messages.info(request, "Payment was cancelled.")
    return redirect('cart')

#=======================================================================

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from payments.gateway_factory import get_gateway

@csrf_exempt
def phonepe_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'FAILED', 'error': 'Invalid HTTP method'}, status=405)

    try:
        # Fetch active PhonePe payment method and its config
        payment_method = get_object_or_404(PaymentMethod, name='phonepe', is_active=True)
        gateway = get_gateway(payment_method.name)

        # Let the gateway handle the verification & parsing
        result = gateway.verify_payment(request)

        if result['status'] == 'success':
            # Update payment and order status here
            payment = Payment.objects.get(reference_id=result.get('reference_id'))

            payment.status = 'success'
            payment.transaction_id = result.get('transaction_id')
            payment.save()

            order = payment.order
            order.status = 'paid'
            order.save()

            return JsonResponse({'status': 'OK'}, status=200)
        else:
            # You can log failure details if needed
            return JsonResponse({'status': 'FAILED', 'error': result.get('error')}, status=400)

    except Payment.DoesNotExist:
        return JsonResponse({'status': 'FAILED', 'error': 'Payment record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'FAILED', 'error': str(e)}, status=500)

#======================================================================
#for manualy confirmation of upi payments 


@login_required
def order_pending_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get the latest payment linked to the order (assuming 1 per order)
    payment = order.payments.order_by('-created_at').first()

    return render(
        request,
        'payments/order_pending_confirmation.html',
        {
            'order': order,
            'payment': payment,
        }
    )



@login_required
def update_transaction_id(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payments.order_by('-created_at').first()

    if request.method == 'POST':
        new_txn = request.POST.get('transaction_id', '').strip()
        if new_txn:
            payment.transaction_id = new_txn
            payment.save()
            return redirect('order_pending_confirmation', order_id=order.id)

    return render(request, 'payments/update_transaction_id.html', {
        'order': order,
        'payment': payment,
    })
#===========================================================
from .models import FinancialWallet,Payout
from django.db import transaction


@login_required
def vendor_payout_list(request):
    """Shows all Shopkeepers and the Total Cost Price GramaCart owes them."""
    # Filter wallets for Users who are Shopkeepers/Vendors
    vendor_wallets = FinancialWallet.objects.filter(user__groups__name='Vendor').select_related('user')
    
    return render(request, 'admin_dashboard/vendor_payouts.html', {'wallets': vendor_wallets})

@login_required
def settle_vendor_payout(request, wallet_id):
    """Run this after you send UPI/Cash to the Shopkeeper."""
    wallet = get_object_or_404(FinancialWallet, id=wallet_id)
    
    if request.method == "POST":
        amount_to_pay = wallet.pending_balance
        
        if amount_to_pay > 0:
            with transaction.atomic():
                # 1. Record the Payout
                Payout.objects.create(
                    wallet=wallet,
                    amount=amount_to_pay,
                    reference_number=request.POST.get('txn_id', 'CASH_PAID')
                )
                
                # 2. Update Wallet
                wallet.total_withdrawn += amount_to_pay
                wallet.pending_balance = 0 # Reset debt to zero
                wallet.save()
                
                messages.success(request, f"Paid ₹{amount_to_pay} to {wallet.user.username}")
        else:
            messages.info(request, "No balance to pay for this vendor.")
            
    return redirect('vendor_payout_list')