import sys
from pathlib import Path


URL_IMPORT_OLD = "from . import views"
URL_IMPORT_NEW = "from . import views, summarizer_views"
URL_ANCHOR = '    path("projects/<int:pk>/", views.project_detail, name="project_detail"),\n'
URL_ROUTES = '''    path("projects/<int:pk>/summarize/", summarizer_views.project_summarize, name="project_summarize"),
    path("projects/<int:pk>/summarize/api/analyze/", summarizer_views.analyze_project, name="project_summary_analyze"),
    path("projects/<int:pk>/summarize/api/jobs/", summarizer_views.create_summary_job, name="project_summary_job_create"),
    path("projects/<int:pk>/summarize/api/jobs/<str:job_id>/", summarizer_views.summary_job_status, name="project_summary_job_status"),
    path("projects/<int:pk>/summarize/api/jobs/<str:job_id>/cancel/", summarizer_views.cancel_summary_job, name="project_summary_job_cancel"),
'''

DETAIL_ANCHOR = '''                    <a href="{{ item.pdf_file_en|first_file|upload_url:pdf_folder }}" target="_blank" class="btn-white text-courtNavy border border-slate-200">
                        <i class="fa-regular fa-file-pdf mr-2"></i> English PDF
                    </a>
'''
DETAIL_BUTTON = '''
                    <a href="{% url 'project_summarize' item.pk %}" class="btn-white text-courtNavy border border-slate-200">
                        <i class="fa-solid fa-wand-magic-sparkles mr-2"></i> Summarize
                    </a>
'''

MODEL_CLASS = '''


class ProjectPageSummary(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="page_summaries",
    )
    language = models.CharField(max_length=8, default="en")
    pdf_page = models.PositiveIntegerField()
    printed_page = models.IntegerField(null=True, blank=True)
    page_type = models.CharField(max_length=32, blank=True)
    chapter = models.CharField(max_length=255, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    source_filename = models.CharField(max_length=500)
    source_pdf_sha256 = models.CharField(max_length=64)
    source_text_sha256 = models.CharField(max_length=64)
    source_char_count = models.PositiveIntegerField(default=0)
    extraction_method = models.CharField(max_length=32, blank=True)
    review_status = models.CharField(max_length=32, default="source_checked")
    summary_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("pdf_page",)
        unique_together = (("project", "language", "pdf_page"),)

    def __str__(self):
        return f"{self.project_id}: {self.language} page {self.pdf_page}"
'''


def atomic_write(path, text):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def patch_urls(path):
    text = path.read_text(encoding="utf-8")
    if "summarizer_views" not in text:
        if URL_IMPORT_OLD not in text:
            raise RuntimeError(f"Could not find publications import in {path}")
        text = text.replace(URL_IMPORT_OLD, URL_IMPORT_NEW, 1)
    if 'name="project_summarize"' not in text:
        if URL_ANCHOR not in text:
            raise RuntimeError(f"Could not find project detail route in {path}")
        text = text.replace(URL_ANCHOR, URL_ANCHOR + URL_ROUTES, 1)
    atomic_write(path, text)


def patch_detail(path):
    text = path.read_text(encoding="utf-8")
    if "{% url 'project_summarize' item.pk %}" in text:
        return
    if DETAIL_ANCHOR not in text:
        raise RuntimeError(f"Could not find English PDF button in {path}")
    atomic_write(path, text.replace(DETAIL_ANCHOR, DETAIL_ANCHOR + DETAIL_BUTTON, 1))


def patch_requirements(path):
    text = path.read_text(encoding="utf-8")
    if not any(line.lower().startswith("pypdf==") for line in text.splitlines()):
        atomic_write(path, text.rstrip() + "\npypdf==4.3.1\n")


def patch_models(path):
    text = path.read_text(encoding="utf-8")
    if "class ProjectPageSummary(" not in text:
        atomic_write(path, text.rstrip() + MODEL_CLASS + "\n")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/www/wwwroot/uscai").resolve()
    if not (root / "manage.py").is_file():
        raise SystemExit(f"Not a Django project: {root}")
    patch_urls(root / "apps/publications/urls.py")
    patch_detail(root / "templates/content/detail.html")
    patch_requirements(root / "requirements.txt")
    patch_models(root / "apps/publications/models.py")
    print("Existing USC files patched.")


if __name__ == "__main__":
    main()
