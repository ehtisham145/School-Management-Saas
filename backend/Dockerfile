FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Requirements come first, so that a code change doesn't reinstall every package.
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

# Settings need these values to load. They are fake and exist only during this one command.
RUN SECRET_KEY=build-only \
    DATABASE_URL=postgres://build:build@localhost/build \
    REDIS_URL=redis://localhost:6379/0 \
    EMAIL_HOST=build \
    CSRF_TRUSTED_ORIGINS=https://build.invalid \
    python manage.py collectstatic --noinput

RUN useradd --system --uid 10001 --no-create-home app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "config.asgi:application", "--worker-class", "uvicorn_worker.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
