from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("email address", blank=True, null=True, unique=True)
    is_platform_admin = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.email = self.email or None
        super().save(*args, **kwargs)


class EmailOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps"
    )
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.purpose} OTP for {self.user}"
