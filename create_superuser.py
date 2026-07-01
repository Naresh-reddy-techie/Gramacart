import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Business.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="GCadmin",
        email="contact.gramacart@gmail.com",
        password="Naresh@2001."
    )
