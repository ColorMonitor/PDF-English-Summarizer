import argparse
import os
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pdf_summarizer_ui.settings")

import django

django.setup()

from summarizer.services import analyze_pdf, load_pages, prepare_page
from summarizer.views import parse_page_selection


def main():
    parser = argparse.ArgumentParser(description="Run focused PDF pipeline checks.")
    parser.add_argument("digital_pdf", type=Path)
    parser.add_argument("scanned_pdf", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="kls_pipeline_test_") as temp_dir:
        mixed_path = Path(temp_dir) / "mixed.pdf"
        encrypted_path = Path(temp_dir) / "encrypted.pdf"

        mixed_writer = PdfWriter()
        mixed_writer.add_page(PdfReader(str(args.digital_pdf)).pages[0])
        mixed_writer.add_page(PdfReader(str(args.scanned_pdf)).pages[0])
        mixed_writer.write(mixed_path)

        mixed_analysis = analyze_pdf(mixed_path)
        assert [page["page_type"] for page in mixed_analysis["pages"]] == [
            "content",
            "ocr_required",
        ]
        prepared = prepare_page(mixed_path, load_pages(mixed_path)[1])
        assert prepared["text_source"] == "ocr"
        assert prepared["text"]

        encrypted_writer = PdfWriter()
        encrypted_writer.add_page(PdfReader(str(args.digital_pdf)).pages[0])
        encrypted_writer.encrypt("test")
        encrypted_writer.write(encrypted_path)
        try:
            analyze_pdf(encrypted_path)
        except ValueError as exc:
            assert "encrypted" in str(exc).lower()
        else:
            raise AssertionError("Encrypted PDF was not rejected.")

    for invalid in ("0", "3-1", "word", "8"):
        try:
            parse_page_selection(invalid, 7)
        except ValueError:
            continue
        raise AssertionError(f"Invalid page selection was accepted: {invalid}")

    print("Mixed PDF: embedded text and OCR paths passed")
    print(f"OCR page: {len(prepared['text'])} characters, classified {prepared['page_type']}")
    print("Encrypted PDF rejection passed")
    print("Invalid page selection checks passed")


if __name__ == "__main__":
    main()
