from payments.gateways.cod import CODGateway
from payments.gateways.paypal import PayPalGateway
from payments.gateways.phonepe import PhonePeGateway
from payments.gateways.razorpay import RazorpayGateway
from payments.gateways.upi_manual import ManualUPIGateway


GATEWAY_REGISTRY = {
    'cod': CODGateway,
    'paypal': PayPalGateway,
    'phonepe': PhonePeGateway,
    'razorpay': RazorpayGateway,
    'upi': ManualUPIGateway,
    # etc...
}

def get_gateway(name):
    normalized_name = name.strip().lower()
    gateway_cls = GATEWAY_REGISTRY.get(normalized_name)
    if not gateway_cls:
        raise ValueError(f"Payment method '{name}' not found in registry.")
    return gateway_cls()



