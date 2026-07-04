from django import forms

from .models import UploadedDocument


class UploadedDocumentForm(forms.ModelForm):
    class Meta:
        model = UploadedDocument
        fields = ["title", "document_type", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.FileInput(attrs={"class": "form-control"}),
        }


class ATSCheckerForm(forms.Form):
    resume = forms.ModelChoiceField(
        queryset=UploadedDocument.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Resume",
    )
    job_description_text = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 8,
                "placeholder": "Paste the job description here...",
            }
        ),
        label="Job Description Text",
        error_messages={
            "required": "Please paste the job description text.",
        },
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["resume"].queryset = UploadedDocument.objects.filter(
            user=user,
            document_type=UploadedDocument.RESUME,
        ).order_by("-version", "-uploaded_at")
