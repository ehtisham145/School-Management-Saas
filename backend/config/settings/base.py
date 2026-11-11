from pathlib import Path

import environ
from celery.schedules import crontab

# settings/base.py -> settings -> config -> backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# ---------------------------------------------------------------- Apps
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "channels",
    "axes",
]
LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.academics",
    "apps.audit",
    "apps.core",
    "apps.platform",
    "apps.tenancy",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenancy.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------- Database
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Lesson Lab <info@lessonlab.me>")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = 15
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
LEADS_EMAIL = env("LEADS_EMAIL", default="info@lessonlab.me")

# Branded emails (apps/integrations/email/branded.py). A blank value hides that footer part.
COMPANY_NAME = "Lesson Lab"
COMPANY_WEBSITE = env("COMPANY_WEBSITE", default=FRONTEND_URL).rstrip("/")
COMPANY_ADDRESS = env("COMPANY_ADDRESS", default="")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="support@lessonlab.me")
BRAND_HEADER_LABEL = env("BRAND_HEADER_LABEL", default="School Management")
# Blank attaches the logo to each email. A value must be an absolute, public URL.
BRAND_LOGO_URL = env("BRAND_LOGO_URL", default="")
BRAND_LOGO_WIDTH = 155
BRAND_LOGO_HEIGHT = 36
# Shown on quotation PDFs. Blank hides it.
COMPANY_VAT_NUMBER = env("COMPANY_VAT_NUMBER", default="")

# Quotations: Saudi VAT is 15%. A quotation keeps the rate it was made with.
QUOTATION_VAT_RATE = env("QUOTATION_VAT_RATE", default="15.00")
QUOTATION_VALID_DAYS = env.int("QUOTATION_VALID_DAYS", default=30)

# Audit log: read the client IP from X-Forwarded-For only behind a proxy that sets it
# itself (Caddy in production). Locally there is no proxy, so REMOTE_ADDR is right.
TRUST_X_FORWARDED_FOR = False

# ---------------------------------------------------------------- Passwords
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------- Login lockout (django-axes)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # must be first
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 15
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]

# ---------------------------------------------------------------- Language & time
LANGUAGE_CODE = "en"
LANGUAGES = [("ar", "العربية"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "Asia/Riyadh"
USE_TZ = True

# ---------------------------------------------------------------- Static & media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------- API
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {"login": "20/min", "email_code": "50/min", "leads": "10/hour"},
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Lesson Lab API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------- Redis (optional locally)
# Without REDIS_URL everything falls back to in-memory (laptop mode).
REDIS_URL = env("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
    CELERY_BROKER_URL = REDIS_URL
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    CELERY_BROKER_URL = "memory://"
    CELERY_TASK_ALWAYS_EAGER = True

CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_BEAT_SCHEDULE = {
    # Just after midnight, Saudi time.
    "expire-overdue-subscriptions": {
        "task": "apps.platform.tasks.expire_overdue_subscriptions_task",
        "schedule": crontab(hour=0, minute=15),
    },
}
