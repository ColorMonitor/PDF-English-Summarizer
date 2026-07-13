from django.urls import include, path


urlpatterns = [
    path("", include("summarizer.urls")),
]

