from django.db import models


class Lead(models.Model):
    name = models.CharField(max_length=120)
    school_name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    is_handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class DemoRequest(Lead):
    class Plan(models.TextChoices):
        BASIC = "basic", "Basic"
        PREMIUM = "premium", "Premium"
        ADVANCED = "advanced", "Advanced"

    phone = models.CharField(max_length=30, blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, blank=True)
    message = models.TextField(max_length=2000, blank=True)


class ContactMessage(Lead):
    school_name = models.CharField(max_length=200, blank=True)
