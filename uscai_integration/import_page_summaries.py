import argparse
import json
import os
import re
import sys
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_data(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    document = data.get("document", {})
    pages = data.get("pages", [])
    if document.get("page_count") != len(pages):
        raise ValueError("Document page count does not match the summary records.")
    if [page.get("pdf_page") for page in pages] != list(range(1, len(pages) + 1)):
        raise ValueError("Summary pages must be complete and sequential.")
    if not SHA256.fullmatch(document.get("source_sha256", "")):
        raise ValueError("Invalid source PDF SHA-256.")
    for page in pages:
        if not str(page.get("summary", "")).strip():
            raise ValueError(f"Page {page.get('pdf_page')} has no summary.")
        if not SHA256.fullmatch(page.get("source_text_sha256", "")):
            raise ValueError(f"Page {page.get('pdf_page')} has an invalid source hash.")
    return document, pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--project-id", required=True, type=int)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not (target / "manage.py").is_file():
        raise SystemExit(f"Not a Django project: {target}")
    sys.path.insert(0, str(target))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    django.setup()

    from django.db import transaction
    from django.utils import timezone
    from apps.core.templatetags.usc_tags import first_file
    from apps.publications.models import Project, ProjectPageSummary

    document, pages = load_data(Path(args.data))
    project = Project.objects.get(pk=args.project_id)
    project_filename = Path(first_file(project.pdf_file_en)).name
    if project_filename != document["source_filename"]:
        raise ValueError(
            f"Project PDF mismatch: {project_filename!r} != {document['source_filename']!r}"
        )

    now = timezone.now()
    created_count = 0
    updated_count = 0
    with transaction.atomic():
        for page in pages:
            record, created = ProjectPageSummary.objects.update_or_create(
                project=project,
                language=document["summary_language"],
                pdf_page=page["pdf_page"],
                defaults={
                    "printed_page": page.get("printed_page"),
                    "page_type": page.get("page_type", ""),
                    "chapter": page.get("chapter") or "",
                    "section_title": page.get("section_title") or "",
                    "summary": page["summary"].strip(),
                    "source_filename": document["source_filename"],
                    "source_pdf_sha256": document["source_sha256"],
                    "source_text_sha256": page["source_text_sha256"],
                    "source_char_count": page.get("source_char_count", 0),
                    "extraction_method": page.get("extraction_method", ""),
                    "review_status": page.get("review_status", "source_checked"),
                    "summary_version": page.get("summary_version", document.get("summary_version", 1)),
                    "updated_at": now,
                },
            )
            if created:
                record.created_at = now
                record.save(update_fields=["created_at"])
                created_count += 1
            else:
                updated_count += 1

    stored_count = ProjectPageSummary.objects.filter(
        project=project,
        language=document["summary_language"],
        source_filename=document["source_filename"],
    ).count()
    if stored_count != len(pages):
        raise RuntimeError(f"Expected {len(pages)} stored pages, found {stored_count}.")
    print(f"Imported {stored_count} pages: {created_count} created, {updated_count} updated.")


if __name__ == "__main__":
    main()
