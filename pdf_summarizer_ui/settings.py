import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-dev-only-pdf-summarizer")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "summarizer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pdf_summarizer_ui.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "pdf_summarizer_ui.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Rangoon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DOCUMENT_WORK_DIR = BASE_DIR / "tmp" / "documents"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 512 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

MODEL_DIR = Path(os.environ.get("MODEL_DIR", r"E:\KLS_ai\model"))
SOURCE_PDF_ALLOWED_HOSTS = {
    host.strip() for host in os.environ.get("SOURCE_PDF_ALLOWED_HOSTS", "www.unionsupremecourt.gov.mm").split(",") if host.strip()
}
MAX_PAGE_INPUT_TOKENS = 2048
MAX_SUMMARY_TOKENS = 256
MIN_SUMMARIZABLE_CHARS = 180
MIN_SUMMARY_TOKENS = 32
SUMMARY_SOURCE_TOKEN_RATIO = 0.35
