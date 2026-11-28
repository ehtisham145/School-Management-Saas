from pathlib import Path

import environ
from celery.schedules import crontab

from config.settings.guards import env_decimal

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
    "apps.chatbot",
    "apps.classroom",
    "apps.browser_agent",
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
# ASGI runs each request in its own thread, so persistent connections pile up
# until Postgres runs out of processes. Django's docs say to disable them under ASGI.
DATABASES["default"]["CONN_MAX_AGE"] = 0
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Classes, students, attendance, marks, report cards and parent messages belong to the
# school plan. The individual teacher's app shows only the AI tools (ADR-0027). Their
# data is kept, so turning this back on brings it back as it was.
TEACHER_CLASSES_ENABLED = False
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

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")

# Browser agent (ADR-0028, docs/browser-agent.md). Off until it is safe for outside users.
BROWSER_AGENT_ENABLED = env.bool("BROWSER_AGENT_ENABLED", default=False)
BROWSER_AGENT_MODEL = env("BROWSER_AGENT_MODEL", default="gpt-4o-mini")
BROWSER_AGENT_MAX_STEPS = env.int("BROWSER_AGENT_MAX_STEPS", default=30)
BROWSER_AGENT_MAX_SECONDS = env.int("BROWSER_AGENT_MAX_SECONDS", default=600)
# A full page is ~3,500-4,500 tokens a step (docs/browser-agent.md §8), so 30 steps need
# about 120k. Money is capped separately by BROWSER_AGENT_MAX_COST_USD_PER_TASK.
BROWSER_AGENT_MAX_INPUT_TOKENS = env.int("BROWSER_AGENT_MAX_INPUT_TOKENS", default=120000)
BROWSER_AGENT_MAX_PAGES = env.int("BROWSER_AGENT_MAX_PAGES", default=5)
BROWSER_AGENT_MAX_STRIKES = env.int("BROWSER_AGENT_MAX_STRIKES", default=3)
BROWSER_AGENT_MAX_PAGE_CHARS = env.int("BROWSER_AGENT_MAX_PAGE_CHARS", default=12000)
# Reply tokens per AI call. Arabic needs room; only tokens actually written are billed.
# A cut-off reply is tried once more with twice this.
BROWSER_AGENT_MAX_OUTPUT_TOKENS = env.int("BROWSER_AGENT_MAX_OUTPUT_TOKENS", default=800)
# USD per million tokens (input, output). Check the provider's price page when they change.
# BROWSER_AGENT_MODEL must be listed here; production refuses to start otherwise.
BROWSER_AGENT_PRICES = {
    "gpt-4o-mini": ("0.15", "0.60"),
    "gpt-4o": ("2.50", "10.00"),
}
# Money is Decimal, never float. A bad value stops start-up (config/settings/guards.py).
BROWSER_AGENT_MAX_COST_USD_PER_TASK = env_decimal(
    env, "BROWSER_AGENT_MAX_COST_USD_PER_TASK", default="0.20"
)
BROWSER_AGENT_MONTHLY_BUDGET_USD = env_decimal(
    env, "BROWSER_AGENT_MONTHLY_BUDGET_USD", default="100"
)
# Concurrency, checked before a task is queued.
BROWSER_AGENT_MAX_RUNNING_PER_USER = env.int("BROWSER_AGENT_MAX_RUNNING_PER_USER", default=1)
BROWSER_AGENT_MAX_RUNNING_TOTAL = env.int("BROWSER_AGENT_MAX_RUNNING_TOTAL", default=10)
# Celery limits for the browser task: soft = the agent's own limit, hard = 30 s later.
BROWSER_AGENT_SOFT_TIME_LIMIT = BROWSER_AGENT_MAX_SECONDS
BROWSER_AGENT_HARD_TIME_LIMIT = BROWSER_AGENT_MAX_SECONDS + 30
# A live-view socket with no traffic for this long is closed.
BROWSER_AGENT_WS_IDLE_SECONDS = env.int("BROWSER_AGENT_WS_IDLE_SECONDS", default=300)
# Domains the agent never opens, with every subdomain. Starting list to review: Saudi banks,
# payment and checkout providers, government identity portals. Setting the env var
# replaces the whole list.
BROWSER_AGENT_BLOCKED_DOMAINS = env.list(
    "BROWSER_AGENT_BLOCKED_DOMAINS",
    default=[
        # Banks
        "alrajhibank.com.sa",
        "alahli.com",
        "riyadbank.com",
        "sab.com",
        "alinma.com",
        "bankalbilad.com",
        "alfransi.com.sa",
        "anb.com.sa",
        "bankaljazira.com",
        "saib.com.sa",
        "stcbank.com.sa",
        # Payments and checkout
        "paypal.com",
        "stripe.com",
        "checkout.com",
        "moyasar.com",
        "hyperpay.com",
        "tap.company",
        "payfort.com",
        "stcpay.com.sa",
        "mada.com.sa",
        "sadad.com",
        "tabby.ai",
        "tamara.co",
        # Government identity
        "absher.sa",
        "iam.gov.sa",
        "nafath.sa",
    ],
)
# Empty means every public domain except the blocked ones.
BROWSER_AGENT_ALLOWED_DOMAINS = env.list("BROWSER_AGENT_ALLOWED_DOMAINS", default=[])
# Ports the agent may open. A URL without a port uses its scheme's default (80/443).
# 8080/8443 are left out on purpose: mostly admin panels, dev servers and proxies.
BROWSER_AGENT_ALLOWED_PORTS = env.list("BROWSER_AGENT_ALLOWED_PORTS", cast=int, default=[80, 443])
# A DNS lookup slower than this refuses the URL instead of holding up the worker.
BROWSER_AGENT_DNS_TIMEOUT_SECONDS = env.float("BROWSER_AGENT_DNS_TIMEOUT_SECONDS", default=3.0)

# Branded emails (apps/integrations/email/branded.py). A blank value hides that footer part.
COMPANY_NAME = "Lesson Lab"
COMPANY_WEBSITE = env("COMPANY_WEBSITE", default=FRONTEND_URL).rstrip("/")
COMPANY_ADDRESS = env("COMPANY_ADDRESS", default="")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="support@lessonlab.me")
BRAND_HEADER_LABEL = env("BRAND_HEADER_LABEL", default="School Management")
# Blank attaches the logo to each email. A value must be an absolute, public URL.
BRAND_LOGO_URL = env("BRAND_LOGO_URL", default="")
BRAND_LOGO_WIDTH = 160
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

# Signed-in sessions end 12 hours after sign-in.
SESSION_COOKIE_AGE = 60 * 60 * 12

# ---------------------------------------------------------------- Login lockout (django-axes)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # must be first
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=15)
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
    "DEFAULT_THROTTLE_RATES": {
        "login": "20/min",
        "email_code": "50/min",
        "teacher_signup": "10/hour",
        "lesson_ai": "20/hour",
        "exam_ai": "20/hour",
        "exam_upload": "30/hour",
        "leads": "10/hour",
        "chatbot": "30/hour",
        "browser_agent": env("BROWSER_AGENT_THROTTLE_RATE", default="10/hour"),
    },
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
# Browser tasks get their own queue and worker, so a slow website never holds up emails
# or subscription jobs (docs/browser-agent.md, "Running the browser worker").
CELERY_TASK_ROUTES = {
    "apps.browser_agent.tasks.run_browser_task_job": {"queue": "browser"},
    "apps.browser_agent.tasks.fail_stale_tasks_task": {"queue": "celery"},
}
CELERY_TASK_ACKS_LATE = True
CELERY_BEAT_SCHEDULE = {
    # Just after midnight, Saudi time.
    "expire-overdue-subscriptions": {
        "task": "apps.platform.tasks.expire_overdue_subscriptions_task",
        "schedule": crontab(hour=0, minute=15),
    },
    # Morning in Saudi Arabia, after the night's expiries have run.
    "send-trial-reminders": {
        "task": "apps.platform.tasks.send_trial_reminders_task",
        "schedule": crontab(hour=9, minute=0),
    },
    # AI test drafts and the PDF text behind them last a day.
    "clean-up-exam-drafts": {
        "task": "apps.classroom.tasks.clean_up_exam_drafts_task",
        "schedule": crontab(minute=30),
    },
    # Browser tasks are never retried, so a worker that died leaves them "running".
    # This marks them failed once they are past the hard time limit.
    "fail-stale-browser-tasks": {
        "task": "apps.browser_agent.tasks.fail_stale_tasks_task",
        "schedule": crontab(minute="*/5"),
    },
}
