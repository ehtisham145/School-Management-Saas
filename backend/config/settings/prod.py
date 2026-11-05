from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import EMAIL_HOST, MIDDLEWARE, REDIS_URL, env

DEBUG = False

if not REDIS_URL:
    raise ImproperlyConfigured("REDIS_URL is required in production")

if not EMAIL_HOST:
    raise ImproperlyConfigured("EMAIL_HOST is required in production")

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# Static files: WhiteNoise goes right after SecurityMiddleware, so HTTPS redirects still apply.
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# HTTPS (Caddy terminates TLS and forwards the protocol header)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
