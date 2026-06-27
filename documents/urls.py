from django.urls import path

from .views import (
    DocumentDeleteView,
    DocumentDetailView,
    DocumentListView,
    DocumentUploadView,
)

app_name = "documents"

urlpatterns = [
    path("documents/", DocumentListView.as_view(), name="document_list"),
    path("documents/upload/", DocumentUploadView.as_view(), name="document_upload"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document_detail"),
    path(
        "documents/<int:pk>/delete/",
        DocumentDeleteView.as_view(),
        name="document_delete",
    ),
]
