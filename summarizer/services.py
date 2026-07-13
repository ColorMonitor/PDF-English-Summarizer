import io
import re
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

import pypdfium2 as pdfium
from django.conf import settings
from pypdf import PdfReader


_model_lock = Lock()
_inference_lock = Lock()
_model_bundle = None
_ml_modules = None


@dataclass
class PageSummary:
    page_number: int
    page_type: str
    char_count: int
    token_count: int
    truncated: bool
    summary: str
    text_source: str = "embedded"
    warning: str = ""

    @property
    def page_type_label(self):
        return self.page_type.replace("_", " ").title()

    def to_dict(self):
        result = asdict(self)
        result["page_type_label"] = self.page_type_label
        return result


def analyze_pdf(pdf_path):
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        raise ValueError("This PDF is encrypted. Remove its password before uploading it.")

    raw_pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        raw_pages.append({"page_number": index, "text": text})

    common_lines = find_common_lines(page["text"] for page in raw_pages)
    pages = []
    for page in raw_pages:
        cleaned = clean_page_text(page["text"], common_lines)
        page_type = classify_page(page["text"], cleaned)
        source = "ocr_pending" if page_type == "ocr_required" else "embedded"
        pages.append(
            {
                "page_number": page["page_number"],
                "page_type": page_type,
                "page_type_label": page_type.replace("_", " ").title(),
                "char_count": len(cleaned),
                "text_source": source,
                "selectable": page_type not in {"blank"},
            }
        )

    return {
        "page_count": len(pages),
        "extracted_characters": sum(page["char_count"] for page in pages),
        "ocr_page_count": sum(page["page_type"] == "ocr_required" for page in pages),
        "ocr_available": ocr_available(),
        "pages": pages,
    }


def load_pages(pdf_path):
    reader = PdfReader(str(pdf_path))
    raw_pages = []
    for index, page in enumerate(reader.pages, start=1):
        raw_pages.append(
            {"page_number": index, "raw_text": normalize_text(page.extract_text() or "")}
        )

    common_lines = find_common_lines(page["raw_text"] for page in raw_pages)
    for page in raw_pages:
        page["text"] = clean_page_text(page["raw_text"], common_lines)
        page["page_type"] = classify_page(page["raw_text"], page["text"])
        page["text_source"] = "embedded"
        page["warning"] = ""
    return raw_pages


def prepare_page(pdf_path, page):
    if page["page_type"] != "ocr_required":
        return page

    if not ocr_available():
        page["warning"] = "OCR is required, but Tesseract is not installed."
        return page

    text = normalize_text(ocr_pdf_page(pdf_path, page["page_number"]))
    page["raw_text"] = text
    page["text"] = text
    page["text_source"] = "ocr"
    page["page_type"] = classify_page(text, text, allow_ocr=False)
    if not text:
        page["page_type"] = "blank"
        page["warning"] = "OCR found no readable English text on this page."
    elif len(text) < settings.MIN_SUMMARIZABLE_CHARS:
        page["warning"] = "OCR recovered only a small amount of text."
    return page


def ocr_available():
    return bool(find_tesseract())


def find_tesseract():
    discovered = shutil.which("tesseract")
    if discovered:
        return discovered
    for candidate in (
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def ocr_pdf_page(pdf_path, page_number):
    with tempfile.TemporaryDirectory(prefix="kls_ocr_") as temp_dir:
        image_path = Path(temp_dir) / "page.png"
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            page = document[page_number - 1]
            bitmap = page.render(scale=300 / 72)
            bitmap.to_pil().save(image_path)
            bitmap.close()
            page.close()
        finally:
            document.close()
        completed = run_tool(
            find_tesseract(),
            [str(image_path), "stdout", "-l", "eng", "--psm", "3"],
        )
        return completed.stdout


def run_tool(executable, arguments):
    if not executable:
        raise RuntimeError("A required document-processing tool is unavailable.")
    command = [executable, *arguments]
    if str(executable).lower().endswith((".cmd", ".bat")):
        command = ["cmd.exe", "/d", "/c", executable, *arguments]
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def normalize_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_common_lines(page_texts):
    counter = Counter()
    page_count = 0
    for text in page_texts:
        page_count += 1
        seen = {normalize_line(line) for line in text.splitlines()}
        counter.update(line for line in seen if 6 <= len(line) <= 90)
    threshold = max(3, int(page_count * 0.15))
    return {line for line, count in counter.items() if count >= threshold}


def normalize_line(line):
    return re.sub(r"\s+", " ", line).strip()


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


def classify_page(raw_text, cleaned_text, allow_ocr=True):
    if not raw_text.strip():
        return "ocr_required" if allow_ocr else "blank"
    if is_table_of_contents(raw_text):
        return "table_of_contents"
    if len(cleaned_text) < settings.MIN_SUMMARIZABLE_CHARS:
        return "title_or_short"
    return "content"


def is_table_of_contents(text):
    lowered = text.lower()
    dot_leaders = len(re.findall(r"\.{8,}", text))
    numbered_entries = len(re.findall(r"(?m)^\s*\(?\d+\)?[.)]?\s+[A-Z]", text))
    page_refs = len(re.findall(r"\.{4,}\s*\d+\b", text))
    return dot_leaders >= 8 and lowered.count("chapter") >= 2 and (page_refs >= 5 or numbered_entries >= 8)


def summarize_non_content_page(page_type, raw_text, cleaned_text):
    if page_type in {"blank", "ocr_required"}:
        return "Blank or decorative page with no extractable text."
    if page_type == "title_or_short":
        title = title_from_short_text(raw_text or cleaned_text)
        return f"Title or short front-matter page: {title}." if title else "Short front-matter page with too little content to summarize reliably."
    if page_type == "table_of_contents":
        entries = extract_toc_entries(raw_text)
        return "Table of contents page listing sections such as: " + "; ".join(entries) + "." if entries else "Table of contents page listing chapters, sections, and page references."
    return ""


def title_from_short_text(text):
    words = collapse_repeated_words(normalize_line(text).split())
    return " ".join(words[:24])


def collapse_repeated_words(words):
    for phrase_len in range(len(words) // 2, 2, -1):
        if words[:phrase_len] == words[phrase_len:phrase_len * 2]:
            return words[:phrase_len] + words[phrase_len * 2:]
    return words


def extract_toc_entries(text):
    entries, seen = [], set()
    for line in text.splitlines():
        candidate = normalize_line(line)
        candidate = re.sub(r"\.{3,}.*$|_+.*$|\s+\d+\s*$", "", candidate).strip()
        if not 8 <= len(candidate) <= 130 or candidate.lower().startswith("case study book"):
            continue
        if not re.search(r"\b(chapter|law|contract|agreement|dispute|transaction|arbitration|company|sale|warranty)\b", candidate, re.I):
            continue
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            entries.append(candidate)
        if len(entries) >= 8:
            break
    return entries


def get_model_bundle():
    global _model_bundle
    if _model_bundle is None:
        with _model_lock:
            if _model_bundle is None:
                _model_bundle = load_model_bundle()
    return _model_bundle


def load_model_bundle():
    torch, auto_tokenizer, auto_model = load_ml_modules()
    model_dir = settings.MODEL_DIR
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory does not exist: {model_dir}")
    tokenizer = auto_tokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = auto_model.from_pretrained(str(model_dir), local_files_only=True)
    align_special_tokens(tokenizer, model)
    preferred = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        model.to(preferred)
        device = preferred
    except RuntimeError:
        model.to("cpu")
        device = "cpu"
    model.eval()
    return {"tokenizer": tokenizer, "model": model, "device": device, "torch": torch}


def load_ml_modules():
    global _ml_modules
    if _ml_modules is None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _ml_modules = (torch, AutoTokenizer, AutoModelForSeq2SeqLM)
    return _ml_modules


def align_special_tokens(tokenizer, model):
    vocab = tokenizer.get_vocab()
    if tokenizer.eos_token is None and "</s>" in vocab:
        tokenizer.eos_token = "</s>"
    if tokenizer.pad_token is None:
        if "<pad>" in vocab:
            tokenizer.pad_token = "<pad>"
        elif tokenizer.eos_token:
            tokenizer.pad_token = tokenizer.eos_token
        else:
            tokenizer.add_special_tokens({"pad_token": "<pad>"})
            model.resize_token_embeddings(len(tokenizer))
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.eos_token_id = tokenizer.eos_token_id
    if getattr(model.config, "decoder_start_token_id", None) is None:
        model.config.decoder_start_token_id = tokenizer.pad_token_id
    if hasattr(model, "generation_config"):
        model.generation_config.pad_token_id = tokenizer.pad_token_id
        model.generation_config.eos_token_id = tokenizer.eos_token_id
        model.generation_config.decoder_start_token_id = model.config.decoder_start_token_id


def summarize_page(bundle, page_number, text, page_type="content", raw_text="", text_source="embedded", warning=""):
    if page_type != "content":
        return PageSummary(page_number, page_type, len(text), 0, False, summarize_non_content_page(page_type, raw_text, text), text_source, warning)
    if not text:
        return PageSummary(page_number, "blank", 0, 0, False, "No extractable text found on this page.", text_source, warning)

    tokenizer, model, device, torch = bundle["tokenizer"], bundle["model"], bundle["device"], bundle["torch"]
    encoded = tokenizer(text, max_length=settings.MAX_PAGE_INPUT_TOKENS, truncation=True, return_tensors="pt")
    token_count = int(encoded["input_ids"].shape[1])
    full_count = len(tokenizer.encode(text, add_special_tokens=True))
    truncated = full_count > settings.MAX_PAGE_INPUT_TOKENS
    encoded = {key: value.to(device) for key, value in encoded.items()}
    try:
        with _inference_lock, torch.no_grad():
            generated = model.generate(
                **encoded,
                max_new_tokens=summary_token_budget(token_count),
                num_beams=4,
                length_penalty=0.8,
                no_repeat_ngram_size=4,
                repetition_penalty=1.08,
                early_stopping=True,
            )
    except RuntimeError as exc:
        if device == "cuda" and "out of memory" in str(exc).lower():
            torch.cuda.empty_cache()
            bundle["model"].to("cpu")
            bundle["device"] = "cpu"
            return summarize_page(bundle, page_number, text, page_type, raw_text, text_source, warning)
        raise
    summary = tokenizer.decode(generated[0], skip_special_tokens=True).strip()
    return PageSummary(page_number, page_type, len(text), token_count, truncated, summary or "The model returned an empty summary for this page.", text_source, warning)


def summary_token_budget(source_tokens):
    budget = max(settings.MIN_SUMMARY_TOKENS, int(source_tokens * settings.SUMMARY_SOURCE_TOKEN_RATIO))
    return min(settings.MAX_SUMMARY_TOKENS, budget)


def summarize_pdf_by_page(uploaded_file, max_pages=None):
    started = time.perf_counter()
    with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary:
        temporary.write(uploaded_file.read())
        temporary.flush()
        pages = load_pages(temporary.name)
        selected = pages[:max_pages] if max_pages else pages
        prepared = [prepare_page(temporary.name, page) for page in selected]
        bundle = get_model_bundle() if any(page["page_type"] == "content" for page in prepared) else None
        summaries = [summarize_page(bundle, page["page_number"], page["text"], page["page_type"], page["raw_text"], page["text_source"], page["warning"]) for page in prepared]
    return {
        "page_count": len(pages), "processed_pages": len(selected),
        "extracted_characters": sum(len(page["text"]) for page in pages),
        "device": bundle["device"] if bundle else "not needed",
        "elapsed_seconds": time.perf_counter() - started, "summaries": summaries,
    }
