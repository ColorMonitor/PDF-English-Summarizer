import sys
import tempfile
import types
import unittest
from pathlib import Path


INTEGRATION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INTEGRATION_ROOT))
sys.modules.setdefault("requests", types.SimpleNamespace())
sys.modules.setdefault("pypdf", types.SimpleNamespace(PdfReader=object))

import patch_existing
from apps.publications import summarizer


class PatcherTests(unittest.TestCase):
    def test_patches_existing_files_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "apps/publications").mkdir(parents=True)
            (root / "templates/content").mkdir(parents=True)
            (root / "manage.py").write_text("", encoding="utf-8")
            urls = root / "apps/publications/urls.py"
            urls.write_text(
                "from django.urls import path\nfrom . import views\n\nurlpatterns = [\n"
                + patch_existing.URL_ANCHOR
                + "]\n",
                encoding="utf-8",
            )
            detail = root / "templates/content/detail.html"
            detail.write_text(patch_existing.DETAIL_ANCHOR, encoding="utf-8")
            requirements = root / "requirements.txt"
            requirements.write_text("Django==4.1\n", encoding="utf-8")
            models = root / "apps/publications/models.py"
            models.write_text(
                "from django.db import models\nfrom apps.core.models import TimeStampedModel\n\n"
                "class Project(TimeStampedModel):\n    pass\n",
                encoding="utf-8",
            )

            patch_existing.patch_urls(urls)
            patch_existing.patch_detail(detail)
            patch_existing.patch_requirements(requirements)
            patch_existing.patch_models(models)
            patch_existing.patch_urls(urls)
            patch_existing.patch_detail(detail)
            patch_existing.patch_requirements(requirements)
            patch_existing.patch_models(models)

            self.assertEqual(urls.read_text(encoding="utf-8").count('name="project_summarize"'), 1)
            self.assertEqual(detail.read_text(encoding="utf-8").count("project_summarize"), 1)
            self.assertEqual(requirements.read_text(encoding="utf-8").count("pypdf==4.3.1"), 1)
            self.assertEqual(models.read_text(encoding="utf-8").count("class ProjectPageSummary("), 1)


class SummarizerTests(unittest.TestCase):
    def test_page_selection(self):
        self.assertEqual(summarizer.parse_page_selection("1-3, 5, 3", 5), [1, 2, 3, 5])
        with self.assertRaises(ValueError):
            summarizer.parse_page_selection("0-2", 5)

    def test_source_url_is_pinned_and_encoded(self):
        value = summarizer.validate_pdf_url(
            "https://www.unionsupremecourt.gov.mm/uploads/projects/Case Study.pdf"
        )
        self.assertIn("Case%20Study.pdf", value)
        with self.assertRaises(ValueError):
            summarizer.validate_pdf_url("https://example.com/file.pdf")

    def test_table_of_contents_detection(self):
        self.assertTrue(summarizer.is_table_of_contents("Table of Contents\nChapter One 1\nChapter Two 4"))

    def test_precomputed_summary_bypasses_beam(self):
        result = summarizer.result_for_page({
            "page_number": 7,
            "page_type": "content",
            "stored_page_type": "annex",
            "char_count": 123,
            "precomputed_summary": "Stored legal summary.",
            "text": "",
        })
        self.assertEqual(result["summary"], "Stored legal summary.")
        self.assertEqual(result["page_type_label"], "Annex")


if __name__ == "__main__":
    unittest.main()
