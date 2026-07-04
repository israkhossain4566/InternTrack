from django.urls import path

from .views import (
    ATSCheckerView,
    ATSResultView,
    DocumentDeleteView,
    DocumentDetailView,
    DocumentListView,
    DocumentUpdateView,
    DocumentUploadView,
)

app_name = "documents"

urlpatterns = [
    path("documents/", DocumentListView.as_view(), name="document_list"),
    path("documents/upload/", DocumentUploadView.as_view(), name="document_upload"),
    path("documents/ats/", ATSCheckerView.as_view(), name="ats_checker"),
    path("documents/ats/result/", ATSResultView.as_view(), name="ats_result"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/edit/", DocumentUpdateView.as_view(), name="document_edit"),
    path(
        "documents/<int:pk>/delete/",
        DocumentDeleteView.as_view(),
        name="document_delete",
    ),
]
