from django.core.exceptions import ImproperlyConfigured

from config.settings.guards import check_production

from .base import *  # noqa: F403
from .base import EMAIL_HOST, MIDDLEWARE, REDIS_URL, REST_FRAMEWORK, env

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
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# CSRF_COOKIE_HTTPONLY stays False: the website reads the CSRF cookie to send X-CSRFToken.
# Start low and raise once HTTPS is proven everywhere (e.g. 86400, then 31536000).
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------- Client IP behind Caddy
# Valid ONLY while Caddy is the sole entry point and the app port (8000) is not reachable
# from the internet. Caddy drops any X-Forwarded-For a client sends and sets the real
# client address itself (staging/caddy/Caddyfile), so exactly one trusted proxy.
# If someone could reach Django directly, they could fake their IP and dodge lockouts.
TRUST_X_FORWARDED_FOR = True
# DRF throttling reads the client from X-Forwarded-For with one proxy in front.
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": env.int("NUM_PROXIES", default=1)}
# django-axes uses the same function as the audit log, so lockouts, throttles and audit
# entries all see the same address. Without this every user would share Caddy's IP and
# one attacker could lock everyone out.
AXES_CLIENT_IP_CALLABLE = "apps.audit.services.axes_client_ip"

# ---------------------------------------------------------------- Browser agent guards
# Model must have a price; enabling needs an OpenAI key and a real Celery queue.
check_production(globals())
