# notifications.py
import firebase_admin
from firebase_admin import credentials, messaging

# Initialize once — put in apps.py ready() method
cred = credentials.Certificate('path/to/firebase-key.json')
firebase_admin.initialize_app(cred)

def send_notification(customer, title, body, url='/'):
    """
    Call this from anywhere in your Django code.
    Works for orders, products, offers — anything.
    """
    tokens = CustomerFCMToken.objects.filter(
        customer=customer
    ).values_list('token', flat=True)

    if not tokens:
        return  # User hasn't enabled notifications

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={'url': url},  # Page to open on tap
        tokens=list(tokens),
    )

    response = messaging.send_each_for_multicast(message)
    print(f'[GC] Sent: {response.success_count}, '
          f'Failed: {response.failure_count}')