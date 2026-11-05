# Build stage: only what the final stage copies from here ships.
FROM python:3.11.18-slim-trixie AS build

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Requirements come first, so that a code change doesn't reinstall every package.
COPY requirements/ requirements/
RUN python -m venv --without-pip /opt/venv \
    && pip --python /opt/venv/bin/python install --no-cache-dir -r requirements/prod.txt

COPY . .

# Settings need these values to load. They are fake and exist only during this one command.
RUN SECRET_KEY=build-only \
    DATABASE_URL=postgres://build:build@localhost/build \
    REDIS_URL=redis://localhost:6379/0 \
    EMAIL_HOST=build \
    CSRF_TRUSTED_ORIGINS=https://build.invalid \
    python manage.py collectstatic --noinput \
    && rm -rf requirements


# Final stage
FROM python:3.11.18-slim-trixie

ARG APP_VERSION=dev
LABEL org.opencontainers.image.source="https://github.com/ehtisham145/School-Management-Saas" \
      org.opencontainers.image.version="$APP_VERSION"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Nothing installs packages at runtime, so the package tools are removed.
# The app user can write only to media/.
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools wheel \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home \
       --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && install -d -o 10001 -g 10001 /app/media

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app /app

USER 10001:10001

EXPOSE 8000

# The headers satisfy ALLOWED_HOSTS and SECURE_SSL_REDIRECT. Compose turns this off for Celery.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8000/api/health/', headers={'Host': os.environ['ALLOWED_HOSTS'].split(',')[0], 'X-Forwarded-Proto': 'https'}), timeout=4)"]

CMD ["gunicorn", "config.asgi:application", "--worker-class", "uvicorn_worker.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--graceful-timeout", "30", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--no-control-socket"]
