import copy
import os
import re
import subprocess
import tempfile
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from urllib.parse import quote, unquote, urlparse, urlunparse

import requests
from pypdf import PdfReader


MIN_SUMMARIZABLE_CHARS = 180
MAX_SOURCE_BYTES = 100 * 1024 * 1024
ALLOWED_PDF_HOST = "www.unionsupremecourt.gov.mm"
DEFAULT_CA_BUNDLE = "/www/wwwroot/uscai/certs/unionsupremecourt-ca-bundle.pem"

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="uscai-summary")
_lock = Lock()
_documents = {}
_jobs = {}


def normalize_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_line(line):
    return re.sub(r"\s+", " ", line).strip()


def find_common_lines(page_texts):
    texts = list(page_texts)
    counter = Counter()
    for text in texts:
        seen = {normalize_line(line) for line in text.splitlines()}
        counter.update(line for line in seen if 6 <= len(line) <= 90)
    threshold = max(3, int(len(texts) * 0.15))
    return {line for line, count in counter.items() if count >= threshold}


def clean_page_text(text, common_lines):
    kept = []
    for line in text.splitlines():
        normalized = normalize_line(line)
        if not normalized or normalized in common_lines:
            continue
        if re.fullmatch(r"-?\s*\d+\s*-?", normalized):
            continue
        kept.append(line)
    cleaned = normalize_text("\n".join(kept))
    cleaned = re.sub(r"\bChapter\s*\(\s*\d+\s*\)\b", " ", cleaned, flags=re.I)
    return normalize_text(cleaned)


def is_table_of_contents(text):
    lowered = text.lower()
    explicit_heading = bool(re.search(r"(?im)^\s*(table of )?contents\s*$", text))
    dot_leaders = len(re.findall(r"\.{4,}\s*\d*", text))
    page_entries = len(re.findall(r"(?m)^.{5,120}\s+\d{1,3}\s*$", text))
    section_words = len(re.findall(r"\b(chapter|part|section|case study)\b", lowered))
    return explicit_heading or (dot_leaders >= 5 and section_words >= 2) or page_entries >= 10


def classify_page(raw_text, cleaned_text):
    if not raw_text.strip():
        return "ocr_required"
    if is_table_of_contents(raw_text):
        return "table_of_contents"
    if len(cleaned_text) < MIN_SUMMARIZABLE_CHARS:
        return "title_or_short"
    return "content"


def extract_toc_entries(text):
    entries = []
    seen = set()
    for line in text.splitlines():
        candidate = normalize_line(line)
        candidate = re.sub(r"\.{3,}.*$|_+.*$|\s+\d+\s*$", "", candidate).strip()
        if not 5 <= len(candidate) <= 130:
            continue
        if candidate.lower() in {"contents", "table of contents"}:
            continue
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            entries.append(candidate)
        if len(entries) == 8:
            break
    return entries


def non_content_summary(page):
    page_type = page["page_type"]
    if page_type == "ocr_required":
        return "No extractable text was found. This page may be scanned, blank, or decorative and requires OCR for further processing."
    if page_type == "table_of_contents":
        entries = extract_toc_entries(page["raw_text"])
        if entries:
            return "Table of contents listing: " + "; ".join(entries) + "."
        return "Table of contents listing the document's sections and page references."
    title = " ".join(normalize_line(page["raw_text"]).split()[:28])
    return f"Title or short front-matter page: {title}." if title else "Short front-matter page."


def validate_pdf_url(value):
    parsed = urlparse(str(value).strip())
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_PDF_HOST:
        raise ValueError("The project PDF source is not allowed.")
    if not unquote(parsed.path).lower().endswith(".pdf"):
        raise ValueError("The project source is not a PDF.")
    encoded_path = quote(unquote(parsed.path), safe="/%")
    return urlunparse(parsed._replace(path=encoded_path, fragment=""))


def download_pdf(source_url, destination):
    ca_bundle = Path(os.getenv("USC_PDF_CA_BUNDLE", DEFAULT_CA_BUNDLE))
    if not ca_bundle.is_file():
        raise RuntimeError(f"PDF CA bundle is missing: {ca_bundle}")
    command = [
        "curl", "--silent", "--show-error", "--fail", "--location",
        "--http1.1", "--tlsv1.2", "--tls-max", "1.2",
        "--cacert", str(ca_bundle), "--retry", "3", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", "240",
        "--max-filesize", str(MAX_SOURCE_BYTES),
        "--user-agent", "Mozilla/5.0", "--output", str(destination),
        validate_pdf_url(source_url),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=260)
    if not destination.is_file() or destination.stat().st_size < 5:
        raise RuntimeError("The project PDF download was empty.")
    with destination.open("rb") as pdf_file:
        if not pdf_file.read(5).startswith(b"%PDF-"):
            raise RuntimeError("The project source did not return a valid PDF.")


def extract_pages(source_url):
    with tempfile.TemporaryDirectory(prefix="uscai_pdf_") as temp_dir:
        pdf_path = Path(temp_dir) / "source.pdf"
        download_pdf(source_url, pdf_path)
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            raise ValueError("This PDF is encrypted.")
        raw_pages = [
            {"page_number": index, "raw_text": normalize_text(page.extract_text() or "")}
            for index, page in enumerate(reader.pages, start=1)
        ]
    common_lines = find_common_lines(page["raw_text"] for page in raw_pages)
    pages = []
    for page in raw_pages:
        text = clean_page_text(page["raw_text"], common_lines)
        page_type = classify_page(page["raw_text"], text)
        pages.append({**page, "text": text, "page_type": page_type})
    return pages


def public_analysis(pages):
    public_pages = []
    for page in pages:
        page_type = page["page_type"]
        public_pages.append({
            "page_number": page["page_number"],
            "page_type": page_type,
            "page_type_label": page_type.replace("_", " ").title(),
            "char_count": page.get("char_count", len(page["text"])),
            "selectable": True,
        })
    return {
        "page_count": len(pages),
        "extracted_characters": sum(page.get("char_count", len(page["text"])) for page in pages),
        "ocr_page_count": sum(page["page_type"] == "ocr_required" for page in pages),
        "ocr_available": False,
        "pages": public_pages,
    }


def register_document(owner, project_id, filename, pages, device="Beam GPU"):
    document_id = uuid.uuid4().hex
    analysis = public_analysis(pages)
    with _lock:
        _documents[document_id] = {
            "owner": owner,
            "project_id": project_id,
            "filename": Path(filename).name,
            "pages": pages,
            "analysis": analysis,
            "device": device,
            "created_at": time.time(),
        }
    return document_id, analysis


def get_document(document_id, owner):
    with _lock:
        document = _documents.get(document_id)
        if not document or document["owner"] != owner:
            return None
        return copy.deepcopy(document)


def parse_page_selection(value, page_count):
    selected = set()
    for part in str(value).split(","):
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


def beam_summary(page):
    endpoint = os.getenv("BEAM_ENDPOINT_URL", "").strip()
    token = os.getenv("BEAM_API_TOKEN", "").strip()
    if not endpoint or not token:
        raise RuntimeError("Beam endpoint settings are missing.")
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
        json={"page_number": page["page_number"], "text": page["text"]},
        timeout=(20, 240),
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    if not isinstance(data, dict) or not data.get("summary"):
        raise RuntimeError("Beam returned an invalid summary response.")
    return data


def start_job(document_id, owner, page_numbers):
    document = get_document(document_id, owner)
    if not document:
        raise ValueError("This document analysis expired. Reload the page.")
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "owner": owner,
        "status": "queued",
        "stage": "Waiting to start",
        "current_page": None,
        "completed": 0,
        "total": len(page_numbers),
        "percent": 0,
        "device": document.get("device", "Beam GPU"),
        "results": [],
        "error": "",
        "cancel_requested": False,
    }
    with _lock:
        _jobs[job_id] = job
    _executor.submit(run_job, job_id, document, page_numbers)
    return public_job(job_id, owner)


def result_for_page(page):
    if "precomputed_summary" in page:
        return {
            "page_number": page["page_number"],
            "page_type": page["page_type"],
            "page_type_label": page.get("stored_page_type", page["page_type"]).replace("_", " ").title(),
            "char_count": page.get("char_count", 0),
            "token_count": 0,
            "truncated": False,
            "summary": page["precomputed_summary"],
            "warning": "",
        }
    if page["page_type"] == "content":
        result = beam_summary(page)
        return {
            "page_number": page["page_number"],
            "page_type": page["page_type"],
            "page_type_label": "Content",
            "char_count": len(page["text"]),
            "token_count": int(result.get("token_count", 0)),
            "truncated": bool(result.get("truncated", False)),
            "summary": result["summary"],
            "warning": "",
        }
    return {
        "page_number": page["page_number"],
        "page_type": page["page_type"],
        "page_type_label": page["page_type"].replace("_", " ").title(),
        "char_count": len(page["text"]),
        "token_count": 0,
        "truncated": False,
        "summary": non_content_summary(page),
        "warning": "OCR is not enabled for this demo." if page["page_type"] == "ocr_required" else "",
    }


def run_job(job_id, document, page_numbers):
    started = time.perf_counter()
    pages = {page["page_number"]: page for page in document["pages"]}
    try:
        update_job(job_id, status="running", stage="Preparing selected pages")
        for position, page_number in enumerate(page_numbers, start=1):
            if is_cancelled(job_id):
                update_job(job_id, status="cancelled", stage="Cancelled", current_page=None)
                return
            update_job(job_id, stage=f"Summarizing page {page_number}", current_page=page_number)
            result = result_for_page(pages[page_number])
            with _lock:
                job = _jobs[job_id]
                job["results"].append(result)
                job["completed"] = position
                job["percent"] = round(position * 100 / len(page_numbers))
        update_job(
            job_id,
            status="completed",
            stage="Completed",
            current_page=None,
            elapsed_seconds=round(time.perf_counter() - started, 1),
        )
    except Exception as exc:
        update_job(job_id, status="failed", stage="Failed", current_page=None, error=str(exc))


def update_job(job_id, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def public_job(job_id, owner):
    with _lock:
        job = _jobs.get(job_id)
        if not job or job["owner"] != owner:
            return None
        result = copy.deepcopy(job)
        result.pop("owner", None)
        result.pop("cancel_requested", None)
        return result


def cancel_job(job_id, owner):
    with _lock:
        job = _jobs.get(job_id)
        if not job or job["owner"] != owner:
            return False
        if job["status"] in {"queued", "running"}:
            job["cancel_requested"] = True
            job["stage"] = "Cancellation requested"
        return True


def is_cancelled(job_id):
    with _lock:
        return _jobs[job_id]["cancel_requested"]
