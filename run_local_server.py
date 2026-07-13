import os
from wsgiref.simple_server import make_server

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pdf_summarizer_ui.settings")

application = StaticFilesHandler(get_wsgi_application())

with make_server("127.0.0.1", 8000, application) as server:
    print("Serving PDF Summarizer at http://127.0.0.1:8000/", flush=True)
    server.serve_forever()
