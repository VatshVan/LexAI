"""
LexAI base settings shared across environments.
"""
from pathlib import Path

import environ
import structlog

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://localhost:5173"]),
    MAX_UPLOAD_SIZE_MB=(int, 50),
    EMBEDDING_BATCH_SIZE=(int, 32),
    CHROMA_PERSIST_DIR=(str, str(BASE_DIR / "chroma_data")),
    MEDIA_ROOT=(str, str(BASE_DIR / "media")),
    EXPORT_ROOT=(str, str(BASE_DIR / "media" / "exports")),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/0"),
    CELERY_RESULT_BACKEND=(str, "redis://localhost:6379/0"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    VOYAGE_API_KEY=(str, ""),
    ANTHROPIC_API_KEY=(str, ""),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "django_filters",
    "django_celery_results",
    "django_extensions",
    "drf_spectacular",
    "apps.core",
    "apps.documents",
    "apps.vector_store",
    "apps.agents",
    "apps.orchestration",
    "apps.templates_engine",
    "apps.claude_client",
    "apps.verification.apps.VerificationConfig",
    "apps.compilation",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static_collected"
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.lexai_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

CORS_ALLOWED_ORIGINS = env(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540

CHROMA_PERSIST_DIR = env("CHROMA_PERSIST_DIR")

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = env("VOYAGE_API_KEY", default="")
CLAUDE_SONNET_MODEL = env("CLAUDE_SONNET_MODEL", default="claude-sonnet-4-6")
CLAUDE_HAIKU_MODEL = env(
    "CLAUDE_HAIKU_MODEL",
    default="claude-haiku-4-5-20251001",
)
CLAUDE_HAIKU_MAX_TOKENS = env.int("CLAUDE_HAIKU_MAX_TOKENS", default=512)
CLAUDE_SONNET_MAX_TOKENS = env.int("CLAUDE_SONNET_MAX_TOKENS", default=1024)
CLAUDE_TEMPERATURE = env.float("CLAUDE_TEMPERATURE", default=0.1)
CLAUDE_MAX_RETRIES = env.int("CLAUDE_MAX_RETRIES", default=3)

VOYAGE_EMBEDDING_MODEL = env("VOYAGE_EMBEDDING_MODEL", default="voyage-law-2")
EMBEDDING_BATCH_SIZE = env.int("EMBEDDING_BATCH_SIZE", default=32)

DEFAULT_TOP_K = env.int("DEFAULT_TOP_K", default=8)
MIN_RELEVANCE_SCORE = env.float("MIN_RELEVANCE_SCORE", default=0.38)
MAX_CHUNK_TOKENS_PER_CALL = env.int("MAX_CHUNK_TOKENS_PER_CALL", default=2500)
COSINE_VERIFIED_THRESHOLD = env.float("COSINE_VERIFIED_THRESHOLD", default=0.82)
COSINE_HALLUCINATED_THRESHOLD = env.float(
    "COSINE_HALLUCINATED_THRESHOLD",
    default=0.45,
)
PURGE_SCORE_THRESHOLD = env.float("PURGE_SCORE_THRESHOLD", default=0.35)
CONTRADICTION_PURGE_THRESHOLD = env.float(
    "CONTRADICTION_PURGE_THRESHOLD",
    default=0.80,
)

EXPORT_ROOT = env("EXPORT_ROOT", default=str(BASE_DIR / "media" / "exports"))
SHOW_API_DOCS = env.bool("SHOW_API_DOCS", default=True)
USE_CLOUDINARY = env.bool("USE_CLOUDINARY", default=False)

MAX_UPLOAD_SIZE_MB = env("MAX_UPLOAD_SIZE_MB")
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES

ALLOWED_UPLOAD_MIME_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 86400,
    }
}

SPECTACULAR_SETTINGS = {
    "TITLE": "LexAI API",
    "DESCRIPTION": "AI-Powered Legal Paralegal - Indian Legal Domain",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
