"""Production settings.

Activate with: DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

DEBUG = env("DEBUG", default=False)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=[])

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"

# PostgreSQL via DATABASE_URL, e.g. postgres://user:pass@localhost:5432/student_pms
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///" + str(BASE_DIR / "db.sqlite3"))
}

# Shared cache (database-backed) so django-axes lockouts work across gunicorn workers.
# Requires: python manage.py createcachetable (run in the Render build script).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_axes_cache",
    }
}

# SMTP (configure EMAIL_HOST* on Render to send real verification/reset emails).
# If no host is set, fall back to the console backend so registration never
# crashes — the email is instead printed to the deploy/startup logs.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
