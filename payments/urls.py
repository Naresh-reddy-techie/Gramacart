from django.urls  import path
from .import views

urlpatterns = [
    path('payment/<int:order_id>/', views.payment_view, name='payment'),

    path('paypal/success', views.paypal_success, name='paypal_success'),
    path('paypal/cancel', views.paypal_cancel, name='paypal_cancel'),

    path('payment/phonepe/webhook/', views.phonepe_webhook, name='phonepe-webhook'),

    # ✅ Show after UPI payment and txn_id is submitted
    path('order/pending/<int:order_id>/', views.order_pending_confirmation, name='order_pending_confirmation'),
    #if they entered wrong transaction id
    path('order/<int:order_id>/update_txn/', views.update_transaction_id, name='update_transaction_id'),

    
    # ADMIN: Vendor specific list
    path('admin/vendor-payouts/', views.vendor_payout_list, name='vendor_payout_list'),
    path('admin/settle-vendor/<int:wallet_id>/', views.settle_vendor_payout, name='settle_vendor_payout'),



]