from .base import BasePaymentGateway

class ManualUPIGateway(BasePaymentGateway):
    def initiate_payment(self, order, config: dict) -> dict:
        upi_id = config.get('upi_id')
        payee_name = config.get('payee_name', 'Merchant')
        amount = str(order.total)

        upi_uri = (
            f"upi://pay?"
            f"pa={upi_id}&pn={payee_name}&am={amount}&cu=INR"
        )

        return {
            "status": "pending",
            "reference_id": f"UPI-{order.id}",
            "upi_uri": upi_uri,
            "upi_id": upi_id,
            "payee_name": payee_name,
            "amount": amount,
        }

    def verify_payment(self, request) -> dict:
        txn_id = request.POST.get("txn_id")
        if not txn_id:
            return {"status": "failed", "error": "Transaction ID is required"}

        return {
            "status": "success",
            "transaction_id": txn_id
        }

    def supports_webhook(self) -> bool:
        return False
