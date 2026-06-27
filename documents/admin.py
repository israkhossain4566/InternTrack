from django.contrib import admin

from .models import UploadedDocument


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "document_type", "version", "uploaded_at")
    list_filter = ("document_type", "uploaded_at")
    search_fields = ("title", "user__username")
