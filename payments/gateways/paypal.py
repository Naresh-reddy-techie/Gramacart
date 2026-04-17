import requests
from .base import BasePaymentGateway

class PayPalGateway(BasePaymentGateway):
    BASE_URL = "https://api.sandbox.paypal.com"  # Switch to live in prod

    def get_access_token(self, config):
        response = requests.post(
            f"{self.BASE_URL}/v1/oauth2/token",
            auth=(config['client_id'], config['client_secret']),
            data={'grant_type': 'client_credentials'}
        )
        data = response.json()
        if 'access_token' not in data:
            raise Exception(f"Access token error: {data}")
        return data['access_token']

    def initiate_payment(self, order, config: dict) -> dict:
        token = self.get_access_token(config)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": config.get("currency", "USD"),
                    "value": str(order.total)
                }
            }],
            "application_context": {
                "return_url": "http://localhost:8000/payment/paypal/success",
                "cancel_url": "http://localhost:8000/payment/paypal/cancel"
            }
        }

        response = requests.post(
            f"{self.BASE_URL}/v2/checkout/orders",
            json=payload,
            headers=headers
        )

        data = response.json()

        if 'links' not in data:
            raise Exception(f"Invalid PayPal response: {data}")

        approval_url = next((link['href'] for link in data['links'] if link['rel'] == 'approve'), None)

        return {
            "status": "pending",
            "reference_id": data.get('id'),
            "redirect_url": approval_url
        }

    def verify_payment(self, request) -> dict:
        token = request.GET.get('token')
        if not token:
            return {'status': 'failed', 'error': 'Missing token'}

        from payments.models import Payment, PaymentMethod

        try:
            payment = Payment.objects.get(reference_id=token)
            config = payment.method.config
        except Payment.DoesNotExist:
            return {'status': 'failed', 'error': 'Payment not found'}

        access_token = self.get_access_token(config)

        response = requests.post(
            f"{self.BASE_URL}/v2/checkout/orders/{token}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code >= 400:
            return {'status': 'failed', 'error': f"PayPal API error: {response.text}"}

        data = response.json()

        try:
            transaction_id = data['purchase_units'][0]['payments']['captures'][0]['id']
            return {
                "status": "success",
                "transaction_id": transaction_id
            }
        except (KeyError, IndexError):
            return {'status': 'failed', 'error': 'Invalid capture response'}

    def supports_webhook(self) -> bool:
        return True
