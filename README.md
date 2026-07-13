# PDF English Summarizer

Django UI for page-by-page PDF summarization with OCR support and a local LongT5 model.

## Local run

```powershell
.\.venv\Scripts\activate
python run_local_server.py
```

Open `http://127.0.0.1:8000/`.

## Server env

Set these before running with Gunicorn or another WSGI server:

```bash
DJANGO_SECRET_KEY=change-this
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
MODEL_DIR=/www/models/kls_ai/model
```

Do not commit the trained model, `.venv`, uploads, logs, or `.env`.
