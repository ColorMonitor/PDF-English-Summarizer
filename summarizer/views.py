import json
import tempfile
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .jobs import cancel_job, get_document, public_job, register_document, start_job
from .services import analyze_pdf


def index(request):
    return render(request, "summarizer/index.html")


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
