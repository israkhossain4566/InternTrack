import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


def validate_document_extension(file):
    allowed_extensions = [".pdf", ".doc", ".docx"]
    extension = os.path.splitext(file.name)[1].lower()

    if extension not in allowed_extensions:
        raise ValidationError("Only PDF, DOC, and DOCX files are allowed.")


def validate_document_size(file):
    max_size = 5 * 1024 * 1024

    if file.size > max_size:
        raise ValidationError("File size must not be more than 5 MB.")


class UploadedDocument(models.Model):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    OTHER = "other"

    DOCUMENT_TYPE_CHOICES = [
        (RESUME, "Resume"),
        (COVER_LETTER, "Cover Letter"),
        (OTHER, "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(
        upload_to="documents/",
        validators=[validate_document_extension, validate_document_size],
    )
    version = models.PositiveIntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} (v{self.version})"
