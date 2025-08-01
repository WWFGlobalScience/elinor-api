import os
import sys
from pathlib import Path

ENVIRONMENT = os.environ.get("ENV").lower()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = False
DEBUG_LEVEL = "ERROR"
_allowed_hosts = os.environ.get("ALLOWED_HOSTS") or ""
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(",")]
_admins = os.environ.get("ADMINS") or ""
ADMINS = [("Elinor admin", admin.strip()) for admin in _admins.split(",")]
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
API_DOMAIN = "https://dev-api.elinordata.org"
FRONTEND_DOMAIN = "https://elinordata.org"
if ENVIRONMENT != "prod":
    API_DOMAIN = "https://dev-api.elinordata.org"
    FRONTEND_DOMAIN = "https://dev.elinordata.org"
if ENVIRONMENT not in ("prod", "dev"):
    DEBUG = True
    DEBUG_LEVEL = "DEBUG"
    ALLOWED_HOSTS = ["*"]
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    API_DOMAIN = "http://localhost:8082"
    FRONTEND_DOMAIN = "http://localhost:3000"


# Application definition

INSTALLED_APPS = [
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework_gis",
    "django_filters",
    "django_extensions",
    "api.apps.ApiConfig",
    "tools",
    "django_countries",
    "corsheaders",
    "drf_recaptcha",
    # authentication
    "rest_framework.authtoken",
    "dj_rest_auth",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "dj_rest_auth.registration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "api/templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("DB_NAME") or "api",
        "USER": os.environ.get("DB_USER") or "postgres",
        "PASSWORD": os.environ.get("DB_PASSWORD") or "postgres",
        "HOST": os.environ.get("DB_HOST") or "localhost",
        "PORT": os.environ.get("DB_PORT") or "5432",
    }
}
if ENVIRONMENT in ("dev", "prod"):
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

gettext = lambda s: s
LANGUAGES = (
    ("en", gettext("English")),
    ("es", gettext("Español")),
    ("id", gettext("Bahasa Indonesia")),
    ("pt", gettext("Portuguese")),
    ("sw", gettext("Kiswahili")),
    ("fr", gettext("French")),
)
MODELTRANSLATION_FALLBACK_LANGUAGES = {
    "default": ("en", "es", "id", "pt", "sw","fr"),
}


# App settings

APPNAME = "elinor"
SITE_ID = 1
GEO_PRECISION = 6  # to nearest 10 cm
ATTRIBUTE_NORMALIZER = 10
EXCEL_MIME_TYPES = ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
ZIP_MIME_TYPES = ["application/zip", "application/x-zip-compressed"]
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PERMISSION_CLASSES": ("api.permissions.DefaultPermission",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",  #
    ),
    "EXCEPTION_HANDLER": "api.resources.api_exception_handler",
    "NON_FIELD_ERRORS_KEY": "non_field_errors",
}

CORS_ORIGIN_ALLOW_ALL = True

AWS_BACKUP_BUCKET = os.environ.get("AWS_BACKUP_BUCKET")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = AWS_S3_REGION_NAME = os.environ.get("AWS_REGION")
S3_DBBACKUP_MAXAGE = 60  # days
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_LOCATION = f"{ENVIRONMENT}/"
AWS_QUERYSTRING_AUTH = False

EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "Elinor <{}>".format(EMAIL_HOST_USER)
EMAIL_CONTACT = os.environ.get("EMAIL_CONTACT")
DRF_RECAPTCHA_SECRET_KEY = os.environ.get("DRF_RECAPTCHA_SECRET_KEY")
# DRF_RECAPTCHA_TESTING = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        "console": {
            "level": DEBUG_LEVEL,
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
    },
    "formatters": {
        "file": {"format": "%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s"}
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "ERROR", "propagate": True},
        "django.security.DisallowedHost": {"handlers": ["null"], "propagate": False},
    },
}


# Authentication

REST_SESSION_LOGIN = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "username_email"

REST_AUTH = {
    "USER_DETAILS_SERIALIZER": "api.resources.base.SelfSerializer",
    "PASSWORD_RESET_SERIALIZER": "api.resources.authuser.FrontendURLPasswordResetSerializer",
    "REGISTER_SERIALIZER": "api.resources.authuser.UserRegistrationSerializer",
}

AUTHENTICATION_BACKENDS = [
    # allauth specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
    # Needed to login by username in Django admin, regardless of allauth
    "django.contrib.auth.backends.ModelBackend",
]
