"""Development settings."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Console email is already the default in base.py. Override via .env for SMTP.
