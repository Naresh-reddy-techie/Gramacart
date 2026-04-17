import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generate_upi_qr_code(upi_id: str, payee_name: str = None, amount: float = None) -> ContentFile:
    """
    Generate UPI QR code image for the given UPI ID and optional amount/payee name.

    Returns a Django ContentFile object (image in PNG format).
    """

    # Construct UPI URI format according to spec:
    # upi://pay?pa=UPI_ID&pn=PayeeName&am=Amount&cu=INR
    # pa = payee address (UPI ID), pn = payee name, am = amount, cu = currency
    upi_uri = f"upi://pay?pa={upi_id}"
    if payee_name:
        upi_uri += f"&pn={payee_name}"
    if amount:
        upi_uri += f"&am={amount:.2f}&cu=INR"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save to bytes buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return ContentFile(buffer.getvalue(), name="upi_qr.png")
