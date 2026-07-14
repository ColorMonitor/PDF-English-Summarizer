import copy
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from django.conf import settings

from .services import get_model_bundle, load_pages, prepare_page, summarize_page


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf-summary")
_lock = Lock()
_documents = {}
_jobs = {}


def document_directory():
    path = Path(settings.DOCUMENT_WORK_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def register_document(uploaded_file, analysis):
    return register_document_path(uploaded_file, uploaded_file.name, analysis)


def register_document_path(source, filename, analysis):
    document_id = uuid.uuid4().hex
    path = document_directory() / f"{document_id}.pdf"
    with path.open("wb") as destination:
        if hasattr(source, "chunks"):
            for chunk in source.chunks():
                destination.write(chunk)
        else:
            with Path(source).open("rb") as source_file:
                destination.write(source_file.read())
    with _lock:
        _documents[document_id] = {
            "path": str(path),
            "filename": Path(filename).name,
            "analysis": analysis,
            "created_at": time.time(),
        }
    return document_id


def get_document(document_id):
    with _lock:
        document = _documents.get(document_id)
        return copy.deepcopy(document) if document else None


def start_job(document_id, page_numbers):
    document = get_document(document_id)
    if not document:
        raise ValueError("The uploaded document is no longer available. Upload it again.")
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "document_id": document_id,
        "filename": document["filename"],
        "status": "queued",
        "stage": "Waiting to start",
        "current_page": None,
        "completed": 0,
        "total": len(page_numbers),
        "percent": 0,
        "device": "not loaded",
        "results": [],
        "error": "",
        "cancel_requested": False,
    }
    with _lock:
        _jobs[job_id] = job
    _executor.submit(run_job, job_id, document, page_numbers)
    return public_job(job_id)


def run_job(job_id, document, page_numbers):
    started = time.perf_counter()
    try:
        pages = {page["page_number"]: page for page in load_pages(document["path"])}
        update_job(job_id, status="running", stage="Preparing selected pages")
        bundle = None
        for position, page_number in enumerate(page_numbers, start=1):
            if is_cancelled(job_id):
                update_job(job_id, status="cancelled", stage="Cancelled")
                return
            page = pages[page_number]
            if page["page_type"] == "ocr_required":
                update_job(job_id, stage=f"Running OCR on page {page_number}", current_page=page_number)
                page = prepare_page(document["path"], page)
            if page["page_type"] == "content" and bundle is None:
                update_job(job_id, stage="Loading summarization model", current_page=page_number)
                bundle = get_model_bundle()
                update_job(job_id, device=bundle["device"])
            update_job(job_id, stage=f"Summarizing page {page_number}", current_page=page_number)
            result = summarize_page(
                bundle, page_number, page["text"], page["page_type"],
                page["raw_text"], page["text_source"], page["warning"],
            ).to_dict()
            with _lock:
                job = _jobs[job_id]
                job["results"].append(result)
                job["completed"] = position
                job["percent"] = round(position * 100 / len(page_numbers))
        update_job(
            job_id, status="completed", stage="Completed", current_page=None,
            elapsed_seconds=round(time.perf_counter() - started, 1),
        )
    except Exception as exc:
        update_job(job_id, status="failed", stage="Failed", error=str(exc), current_page=None)


def update_job(job_id, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def public_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return copy.deepcopy(job) if job else None


def cancel_job(job_id):
    with _lock:
        if job_id not in _jobs:
            return False
        if _jobs[job_id]["status"] in {"queued", "running"}:
            _jobs[job_id]["cancel_requested"] = True
            _jobs[job_id]["stage"] = "Cancellation requested"
        return True


def is_cancelled(job_id):
    with _lock:
        return _jobs[job_id]["cancel_requested"]
