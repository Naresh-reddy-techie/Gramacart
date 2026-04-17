from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.mobile_number} - Verified: {self.is_mobile_verified}"


