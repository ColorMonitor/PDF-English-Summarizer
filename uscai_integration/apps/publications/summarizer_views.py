import json
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.templatetags.usc_tags import first_file, upload_url

from .models import Project, ProjectPageSummary
from .summarizer import (
    cancel_job,
    extract_pages,
    get_document,
    parse_page_selection,
    public_job,
    register_document,
    start_job,
)


def session_owner(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def project_source(project):
    if not project.pdf_file_en:
        raise ValueError("This project has no English PDF.")
    filename = first_file(project.pdf_file_en)
    return filename, upload_url(filename, "projects")


def api_error(message, status=400):
    return JsonResponse({"error": str(message)}, status=status)


STORED_PAGE_TYPES = {
    "toc": "table_of_contents",
    "cover": "title_or_short",
    "foreword": "title_or_short",
    "blank": "title_or_short",
    "annex": "content",
}


def stored_pages(project, filename):
    records = list(ProjectPageSummary.objects.filter(
        project=project,
        language="en",
        source_filename=Path(filename).name,
    ).order_by("pdf_page"))
    if not records:
        return None
    page_numbers = [record.pdf_page for record in records]
    if page_numbers != list(range(1, len(records) + 1)):
        raise RuntimeError("Stored page summaries are incomplete.")
    return [{
        "page_number": record.pdf_page,
        "raw_text": "",
        "text": "",
        "char_count": record.source_char_count,
        "page_type": STORED_PAGE_TYPES.get(record.page_type, record.page_type),
        "stored_page_type": record.page_type,
        "precomputed_summary": record.summary,
    } for record in records]


def project_summarize(request, pk):
    project = get_object_or_404(Project, pk=pk)
    try:
        filename, _ = project_source(project)
    except ValueError as exc:
        return api_error(exc, 404)
    return render(request, "content/project_summarize.html", {
        "item": project,
        "pdf_filename": Path(filename).name,
    })


@require_POST
def analyze_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    try:
        filename, source_url = project_source(project)
        pages = stored_pages(project, filename)
        device = "Stored summaries"
        if pages is None:
            pages = extract_pages(source_url)
            device = "Beam GPU"
        document_id, analysis = register_document(
            session_owner(request), project.pk, filename, pages, device=device
        )
        return JsonResponse({
            "document_id": document_id,
            "filename": Path(filename).name,
            **analysis,
        })
    except Exception as exc:
        return api_error(exc)


@require_POST
def create_summary_job(request, pk):
    project = get_object_or_404(Project, pk=pk)
    try:
        payload = json.loads(request.body or "{}")
        owner = session_owner(request)
        document = get_document(payload.get("document_id", ""), owner)
        if not document or document["project_id"] != project.pk:
            return api_error("This document analysis expired. Reload the page.", 404)
        pages = parse_page_selection(payload.get("pages", ""), document["analysis"]["page_count"])
        return JsonResponse(start_job(payload["document_id"], owner, pages), status=202)
    except (ValueError, json.JSONDecodeError) as exc:
        return api_error(exc)


@require_GET
def summary_job_status(request, pk, job_id):
    get_object_or_404(Project, pk=pk)
    job = public_job(job_id, session_owner(request))
    return JsonResponse(job) if job else api_error("Job not found.", 404)


@require_POST
def cancel_summary_job(request, pk, job_id):
    get_object_or_404(Project, pk=pk)
    if cancel_job(job_id, session_owner(request)):
        return JsonResponse({"cancelled": True})
    return api_error("Job not found.", 404)
