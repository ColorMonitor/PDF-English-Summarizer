from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectPageSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                ("language", models.CharField(default="en", max_length=8)),
                ("pdf_page", models.PositiveIntegerField()),
                ("printed_page", models.IntegerField(blank=True, null=True)),
                ("page_type", models.CharField(blank=True, max_length=32)),
                ("chapter", models.CharField(blank=True, max_length=255)),
                ("section_title", models.CharField(blank=True, max_length=255)),
                ("summary", models.TextField()),
                ("source_filename", models.CharField(max_length=500)),
                ("source_pdf_sha256", models.CharField(max_length=64)),
                ("source_text_sha256", models.CharField(max_length=64)),
                ("source_char_count", models.PositiveIntegerField(default=0)),
                ("extraction_method", models.CharField(blank=True, max_length=32)),
                ("review_status", models.CharField(default="source_checked", max_length=32)),
                ("summary_version", models.PositiveIntegerField(default=1)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="page_summaries", to="publications.project")),
            ],
            options={
                "ordering": ("pdf_page",),
                "unique_together": {("project", "language", "pdf_page")},
            },
        ),
    ]
