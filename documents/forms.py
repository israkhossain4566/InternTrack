from django import forms

from .models import UploadedDocument


class UploadedDocumentForm(forms.ModelForm):
    class Meta:
        model = UploadedDocument
        fields = ["title", "document_type", "file", "version"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "version": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }
