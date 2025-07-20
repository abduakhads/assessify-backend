from .base import *

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(days=1)
SILKY_IGNORE_PATHS = ["/admin/"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "djoser",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "base",
    "api",
    "silk",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'silk.middleware.SilkyMiddleware',
    "config.custom_silk_middleware.CustomSilkyMiddleware",
]
