import json
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlunparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .jobs import cancel_job, get_document, public_job, register_document, register_document_path, start_job
from .services import analyze_pdf


def index(request):
    return render(request, "summarizer/index.html", {"source_url": request.GET.get("source", "")})


@require_POST
def analyze(request):
    uploaded = request.FILES.get("pdf_file")
    if not uploaded:
        return api_error("Choose a PDF file first.")
    if not uploaded.name.lower().endswith(".pdf"):
        return api_error("Only PDF files are supported.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporary:
            for chunk in uploaded.chunks():
                temporary.write(chunk)
            temporary_path = temporary.name
        analysis = analyze_pdf(temporary_path)
        uploaded.seek(0)
        document_id = register_document(uploaded, analysis)
        return JsonResponse({"document_id": document_id, "filename": Path(uploaded.name).name, **analysis})
    except Exception as exc:
        return api_error(str(exc))
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


@require_POST
def analyze_source(request):
    temporary_path = None
    try:
        payload = json.loads(request.body or "{}")
        source_url = validate_source_url(payload.get("source_url", ""))
        filename = Path(unquote(urlparse(source_url).path)).name or "source.pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporary:
            temporary_path = temporary.name
            request_obj = Request(source_url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/pdf,*/*",
                "Connection": "close",
            })
            with urlopen(request_obj, timeout=30) as response:
                content_type = response.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower() and not filename.lower().endswith(".pdf"):
                    raise ValueError("Source URL must point to a PDF.")
                temporary.write(response.read())
        analysis = analyze_pdf(temporary_path)
        document_id = register_document_path(temporary_path, filename, analysis)
        return JsonResponse({"document_id": document_id, "filename": filename, **analysis})
    except (ValueError, json.JSONDecodeError) as exc:
        return api_error(str(exc))
    except Exception as exc:
        return api_error(f"Could not download source PDF: {exc}")
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


def validate_source_url(value):
    source_url = str(value).strip()
    parsed = urlparse(source_url)
    allowed_hosts = getattr(settings, "SOURCE_PDF_ALLOWED_HOSTS", set())
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise ValueError("Source PDF host is not allowed.")
    return urlunparse(parsed._replace(path=quote(unquote(parsed.path))))


@require_POST
def create_job(request):
    try:
        payload = json.loads(request.body or "{}")
        document_id = payload.get("document_id", "")
        document = get_document(document_id)
        if not document:
            return api_error("The uploaded document expired. Upload it again.", 404)
        page_numbers = parse_page_selection(payload.get("pages", ""), document["analysis"]["page_count"])
        return JsonResponse(start_job(document_id, page_numbers), status=202)
    except (ValueError, json.JSONDecodeError) as exc:
        return api_error(str(exc))


@require_GET
def job_status(request, job_id):
    job = public_job(job_id)
    return JsonResponse(job) if job else api_error("Job not found.", 404)


@require_POST
def cancel(request, job_id):
    return JsonResponse({"cancelled": True}) if cancel_job(job_id) else api_error("Job not found.", 404)


def parse_page_selection(value, page_count):
    value = str(value).strip()
    if not value:
        raise ValueError("Choose at least one page.")
    selected = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            pieces = part.split("-", 1)
            if not all(piece.strip().isdigit() for piece in pieces):
                raise ValueError(f"Invalid page range: {part}")
            start, end = (int(piece) for piece in pieces)
            if start > end:
                raise ValueError(f"Page range must be ascending: {part}")
            selected.update(range(start, end + 1))
        elif part.isdigit():
            selected.add(int(part))
        else:
            raise ValueError(f"Invalid page selection: {part}")
    if not selected:
        raise ValueError("Choose at least one page.")
    if min(selected) < 1 or max(selected) > page_count:
        raise ValueError(f"Pages must be between 1 and {page_count}.")
    return sorted(selected)


def api_error(message, status=400):
    return JsonResponse({"error": message}, status=status)
