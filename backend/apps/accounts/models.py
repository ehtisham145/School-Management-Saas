from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("email address", blank=True, null=True, unique=True)
    is_platform_admin = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.email = self.email or None
        super().save(*args, **kwargs)
