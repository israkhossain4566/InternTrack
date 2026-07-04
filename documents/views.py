from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import ATSCheckerForm, UploadedDocumentForm
from .models import UploadedDocument
from .utils import (
    calculate_ats_score,
    extract_uploaded_document_text,
    generate_suggestions,
    get_keyword_analysis,
)


def format_display_datetime(value):
    local_value = timezone.localtime(value)
    hour = local_value.strftime("%I").lstrip("0")

    return f"{local_value:%b} {local_value.day}, {local_value:%Y}, {hour}:{local_value:%M} {local_value:%p}"


class DocumentListView(LoginRequiredMixin, ListView):
    model = UploadedDocument
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return UploadedDocument.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_resume"] = UploadedDocument.objects.filter(
            user=self.request.user,
            document_type=UploadedDocument.RESUME,
        ).order_by("-version", "-uploaded_at").first()
        return context


class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = UploadedDocument
    form_class = UploadedDocumentForm
    template_name = "documents/document_upload.html"
    success_url = reverse_lazy("documents:document_list")

    def form_valid(self, form):
        form.instance.user = self.request.user

        if form.instance.document_type == UploadedDocument.RESUME:
            latest_resume = UploadedDocument.objects.filter(
                user=self.request.user,
                document_type=UploadedDocument.RESUME,
            ).order_by("-version").first()

            if latest_resume is None:
                form.instance.version = 1
            else:
                form.instance.version = latest_resume.version + 1
        else:
            form.instance.version = 1

        return super().form_valid(form)


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = UploadedDocument
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return UploadedDocument.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object

        if document.document_type == UploadedDocument.RESUME:
            resume_versions = UploadedDocument.objects.filter(
                user=self.request.user,
                document_type=UploadedDocument.RESUME,
            ).order_by("-version", "-uploaded_at")

            context["resume_versions"] = resume_versions
            context["latest_resume"] = resume_versions.first()

        return context


class DocumentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = UploadedDocument
    form_class = UploadedDocumentForm
    template_name = "documents/document_form.html"
    context_object_name = "document"
    success_message = "Document updated successfully."

    def get_queryset(self):
        return UploadedDocument.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse("documents:document_detail", kwargs={"pk": self.object.pk})


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = UploadedDocument
    template_name = "documents/document_confirm_delete.html"
    context_object_name = "document"
    success_url = reverse_lazy("documents:document_list")

    def get_queryset(self):
        return UploadedDocument.objects.filter(user=self.request.user)

    def form_valid(self, form):
        document_file = self.object.file
        response = super().form_valid(form)

        if document_file:
            document_file.delete(save=False)

        return response


class ATSCheckerView(LoginRequiredMixin, FormView):
    template_name = "documents/ats_checker.html"
    form_class = ATSCheckerForm
    success_url = reverse_lazy("documents:ats_result")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        resume = form.cleaned_data["resume"]
        job_description_text = form.cleaned_data.get("job_description_text")

        resume_text = extract_uploaded_document_text(resume.file)

        if not resume_text:
            form.add_error(
                "resume",
                "Could not extract text from this resume. Please use a readable PDF, DOC, or DOCX resume.",
            )
            return self.form_invalid(form)

        job_text = job_description_text
        job_source = "Pasted job description"

        if not job_text:
            form.add_error(
                "job_description_text",
                "Please paste the job description text.",
            )
            return self.form_invalid(form)

        match_score = calculate_ats_score(resume_text, job_text)
        matched_keywords, missing_keywords = get_keyword_analysis(resume_text, job_text)
        suggestions = generate_suggestions(missing_keywords)

        self.request.session["ats_result"] = {
            "match_score": match_score,
            "resume_title": resume.title,
            "resume_version": resume.version,
            "resume_filename": resume.file.name,
            "resume_uploaded_at": format_display_datetime(resume.uploaded_at),
            "job_source": job_source,
            "job_word_count": len(job_text.split()),
            "job_character_count": len(job_text),
            "similarity_score": f"{match_score}%",
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "suggestions": suggestions,
            "analysis_date": format_display_datetime(timezone.now()),
        }

        return super().form_valid(form)


class ATSResultView(LoginRequiredMixin, TemplateView):
    template_name = "documents/ats_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.request.session.get("ats_result")

        if result:
            score = result["match_score"]

            if score >= 90:
                progress_class = "bg-success"
            elif score >= 70:
                progress_class = "bg-primary"
            elif score >= 50:
                progress_class = "bg-warning"
            else:
                progress_class = "bg-danger"

            if score >= 90:
                rating_stars = "5"
                rating_label = "Excellent"
            elif score >= 75:
                rating_stars = "4"
                rating_label = "Good"
            elif score >= 60:
                rating_stars = "3"
                rating_label = "Fair"
            else:
                rating_stars = "2"
                rating_label = "Needs Improvement"

            missing_keywords = result.get("missing_keywords", [])
            if missing_keywords:
                missing_text = ", ".join(missing_keywords[:3])
                analysis_summary = (
                    f"Your resume matches {score}% of the job description. "
                    f"Adding {missing_text} experience could improve your ATS compatibility."
                )
            else:
                analysis_summary = (
                    f"Your resume matches {score}% of the job description. "
                    "Your resume already contains the main technical keywords found in this job description."
                )

            context["result"] = result
            context["progress_class"] = progress_class
            context["rating_stars"] = rating_stars
            context["rating_label"] = rating_label
            context["analysis_summary"] = analysis_summary

        return context
