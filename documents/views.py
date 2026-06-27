from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import UploadedDocumentForm
from .models import UploadedDocument


class DocumentListView(LoginRequiredMixin, ListView):
    model = UploadedDocument
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return UploadedDocument.objects.filter(user=self.request.user)


class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = UploadedDocument
    form_class = UploadedDocumentForm
    template_name = "documents/document_upload.html"
    success_url = reverse_lazy("documents:document_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
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
            context["resume_versions"] = UploadedDocument.objects.filter(
                user=self.request.user,
                document_type=UploadedDocument.RESUME,
            ).order_by("-uploaded_at")

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
