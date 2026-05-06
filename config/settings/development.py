"""
LexAI — Development Settings
"""
import os

from .base import *  # noqa: F401, F403

DEBUG = True

# SQLite for dev (already set in base.py via DATABASE_URL default)

# Console renderer for structlog (already set in base)

# CORS — allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Celery's prefork pool is not reliable on Windows; use the solo pool for local dev.
if os.name == "nt":
	CELERY_WORKER_POOL = "solo"
