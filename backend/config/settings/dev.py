from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
# The browser talks to Django through the Next.js dev proxy on port 3000.
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
