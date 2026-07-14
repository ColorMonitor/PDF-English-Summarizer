from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("api/analyze/", views.analyze, name="analyze"),
    path("api/analyze-source/", views.analyze_source, name="analyze_source"),
    path("api/jobs/", views.create_job, name="create_job"),
    path("api/jobs/<str:job_id>/", views.job_status, name="job_status"),
    path("api/jobs/<str:job_id>/cancel/", views.cancel, name="cancel_job"),
]
