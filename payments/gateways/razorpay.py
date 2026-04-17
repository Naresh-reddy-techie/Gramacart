import razorpay
from .base import BasePaymentGateway

class RazorpayGateway(BasePaymentGateway):
    def initiate_payment(self, order, config: dict) -> dict:
        client = razorpay.Client(auth=(config['key_id'], config['key_secret']))

        # Create Razorpay order
        razorpay_order = client.order.create({
            "amount": int(order.total * 100),  # Amount in paise
            "currency": config.get('currency', 'INR'),
            "receipt": f"order_rcptid_{order.id}",
            "payment_capture": 1  # Auto capture
        })

        return {
            "status": "pending",
            "reference_id": razorpay_order['id'],
            "redirect_url": None,  # You’ll open Razorpay checkout from frontend
            "razorpay_order_id": razorpay_order['id'],
            "razorpay_key_id": config['key_id'],
        }

    def verify_payment(self, request) -> dict:
        from payments.models import Payment
        import razorpay

        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        try:
            payment = Payment.objects.get(reference_id=order_id)
            config = payment.method.config
        except Payment.DoesNotExist:
            return {'status': 'failed', 'error': 'Payment not found'}

        client = razorpay.Client(auth=(config['key_id'], config['key_secret']))

        try:
            client.utility.verify_payment_signature({
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            })
        except razorpay.errors.SignatureVerificationError:
            return {'status': 'failed', 'error': 'Signature verification failed'}

        return {
            'status': 'success',
            'transaction_id': payment_id
        }

    def supports_webhook(self) -> bool:
        return True
