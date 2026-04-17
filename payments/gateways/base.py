# payments/gateways/base.py

from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_payment(self, order, config: dict) -> dict:
        """
        Start a payment and return:
        {
            'status': 'success',
            'reference_id': 'xyz',
            'redirect_url': 'https://...'
        }
        """
        pass

    @abstractmethod
    def verify_payment(self, request) -> dict:
        """
        Verify payment from webhook or callback:
        {
            'status': 'success',
            'transaction_id': 'txn_123'
        }
        """
        pass

    @abstractmethod
    def supports_webhook(self) -> bool:
        """
        Return True if this gateway supports webhooks
        """
        pass
