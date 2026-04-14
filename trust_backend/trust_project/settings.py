"""
Django settings for the Trust Analysis backend.
Only the parts needed for this beginner MVP are enabled.
"""
import os
from pathlib import Path

import dj_database_url

# Base directory of the Django project (folder containing manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key secret in production!
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-in-production-trust-mvp-key")

# SECURITY WARNING: True only for local college demos — use False + HTTPS in production.
DEBUG = os.getenv("DEBUG", "1").strip().lower() in ("1", "true", "yes", "on")

# Allow local dev and Vercel deployment domains.
_raw_allowed_hosts = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,.vercel.app,trustbackend-one.vercel.app,trustbackend.vercel.app",
).strip()
ALLOWED_HOSTS = [h.strip() for h in _raw_allowed_hosts.split(",") if h.strip()]

# Apps Django loads for this project.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Lets the browser extension call our API from chrome-extension:// origins.
    "corsheaders",
    # Our small app that holds the /analyze/ view.
    "analyzer",
]

# Middleware runs on every request (order matters).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS must be early so OPTIONS preflight gets correct headers.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Allow any website/extension origin to POST to our API (fine for local class demo).
CORS_ALLOW_ALL_ORIGINS = True

# Allow JSON POST bodies from the extension.
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

ROOT_URLCONF = "trust_project.urls"

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

WSGI_APPLICATION = "trust_project.wsgi.application"

# Database configuration:
# - In production, set DATABASE_URL (Render/Neon/Supabase/Postgres, etc.)
# - Locally, falls back to SQLite for zero setup.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation (default; not used by our API).
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
