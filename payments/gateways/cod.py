from .base import BasePaymentGateway

class CODGateway(BasePaymentGateway):
    def initiate_payment(self, order, config):
        return {
            "status": "success",
            "reference_id": f"COD-{order.id}",
            "redirect_url": None,
        }

    def verify_payment(self, request):
        return {
            "status": "success",
            "transaction_id": "manual-cod"
        }

    def supports_webhook(self):
        return False
