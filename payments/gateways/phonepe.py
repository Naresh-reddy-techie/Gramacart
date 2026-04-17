import hashlib
import hmac
import json
from .base import BasePaymentGateway

class PhonePeGateway(BasePaymentGateway):
    BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"


    def _generate_signature(self, data, salt_key):
        return hmac.new(
            salt_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def initiate_payment(self, order, config: dict) -> dict:
        """
        Initiate PhonePe payment, return dict with status, reference_id, redirect_url.
        Here we mock the API call and signature for demo.
        Replace with real API integration once credentials are available.
        """
        merchant_id = config.get('merchant_id')
        salt_key = config.get('salt_key')
        salt_index = str(config.get('salt_index','1'))

        if not merchant_id or not salt_key:
            raise ValueError("PhonepeGateway config must include 'merchant id' and 'salt key'")
        # Sample payload based on PhonePe docs (simplified)
        payload = {
            "merchantId": merchant_id,  # use local variable from config
            "transactionId": f"order_{order.id}",
            "amount": int(order.total * 100),  # in paise
            "merchantUserId": str(order.user.id),
            "redirectUrl": f"http://localhost:8000/payment/phonepe/callback",
            "callbackUrl": f"http://localhost:8000/payment/phonepe/webhook",
            "merchantSaltIndex": salt_index,  # use local variable
        }


        # Create data string to sign (PhonePe specific)
        data_to_sign = json.dumps(payload, separators=(',', ':'))
        signature = self._generate_signature(data_to_sign, salt_key)

        # Add signature to headers or payload as per PhonePe docs
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": signature
        }

        # Since we don’t have real merchant id/key yet, we mock response
        # Replace below with actual requests.post() to PhonePe endpoint

        # Mock response
        response_data = {
            "status": "SUCCESS",
            "paymentUrl": "https://sandbox-phonepe.payment.url/redirect",
            "transactionId": payload["transactionId"]
        }

        if response_data["status"] == "SUCCESS":
            return {
                "status": "pending",
                "reference_id": response_data["transactionId"],
                "redirect_url": response_data["paymentUrl"]
            }
        else:
            return {
                "status": "failed",
                "error": "PhonePe payment initiation failed."
            }

    def verify_payment(self, request) -> dict:
        """
        Verify payment status.
        This usually happens on webhook or callback from PhonePe.
        Since this is a mock, we just return success for demo.
        Replace with actual verification logic.
        """
        # Example: get transaction id from request params or body
        transaction_id = request.GET.get('transactionId') or request.POST.get('transactionId')
        payment_status = request.GET.get('status') or request.POST.get('status')

        if not transaction_id:
            return {'status': 'failed', 'error': 'Missing transaction ID'}

        # TODO: Verify signature in request to ensure authenticity

        if payment_status == "SUCCESS":
            return {
                "status": "success",
                "transaction_id": transaction_id
            }
        elif payment_status == "FAILURE":
            return {
                "status": "failed",
                "error": "Payment failed at PhonePe"
            }
        else:
            return {
                "status": "pending",
                "transaction_id": transaction_id
            }

    def supports_webhook(self) -> bool:
        return True
