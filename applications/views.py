from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.views.generic import DetailView, ListView

from .models import Company, JobApplication
from .forms import JobApplicationForm, CompanyForm

class ApplicationListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'applications/list.html'
    context_object_name = 'applications'

    def dispatch(self, request, *args, **kwargs):
        self.search_query = request.GET.get('q', '').strip()
        self.status_filter = request.GET.get('status', '').strip()
        self.company_filter = request.GET.get('company', '').strip()
        self.internship_type_filter = request.GET.get('internship_type', '').strip()
        self.deadline_filter = request.GET.get('deadline', '').strip()
        self.date_applied_filter = request.GET.get('date_applied', '').strip()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        applications = JobApplication.objects.filter(user=self.request.user)

        if self.search_query:
            applications = applications.filter(
                Q(company_name__icontains=self.search_query) |
                Q(job_title__icontains=self.search_query) |
                Q(job_location__icontains=self.search_query)
            )

        if self.status_filter:
            applications = applications.filter(status=self.status_filter)

        if self.company_filter:
            applications = applications.filter(company_name=self.company_filter)

        if self.internship_type_filter:
            applications = applications.filter(internship_type=self.internship_type_filter)

        if self.deadline_filter:
            deadline_date = parse_date(self.deadline_filter)
            if deadline_date:
                applications = applications.filter(deadline=deadline_date)

        if self.date_applied_filter:
            application_date = parse_date(self.date_applied_filter)
            if application_date:
                applications = applications.filter(application_date=application_date)

        return applications

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_applications = JobApplication.objects.filter(user=self.request.user)
        filters_active = any([
            self.status_filter,
            self.company_filter,
            self.internship_type_filter,
            self.deadline_filter,
            self.date_applied_filter,
        ])

        context.update({
            'search_query': self.search_query,
            'status_choices': JobApplication.STATUS_CHOICES,
            'company_options': user_applications.exclude(company_name='').order_by(
                'company_name'
            ).values_list('company_name', flat=True).distinct(),
            'internship_type_options': user_applications.exclude(internship_type='').order_by(
                'internship_type'
            ).values_list('internship_type', flat=True).distinct(),
            'status_filter': self.status_filter,
            'company_filter': self.company_filter,
            'internship_type_filter': self.internship_type_filter,
            'deadline_filter': self.deadline_filter,
            'date_applied_filter': self.date_applied_filter,
            'filters_active': filters_active,
            'search_or_filters_active': bool(self.search_query or filters_active),
        })
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if self.company_filter:
            response.set_cookie('most_searched_company', self.company_filter, max_age=86400 * 30)
        elif self.search_query:
            response.set_cookie('most_searched_company', self.search_query, max_age=86400 * 30)
        return response

@login_required
def application_add(request):
    if request.method == 'POST':
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.save()
            return redirect('application_list')
    else:
        form = JobApplicationForm()
    return render(request, 'applications/form.html', {'form': form, 'action': 'Add'})

@login_required
def application_edit(request, pk):
    app = get_object_or_404(JobApplication, pk=pk, user=request.user)
    old_status = app.status
    old_deadline = app.deadline
    old_interview = app.interview_date

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, instance=app)
        if form.is_valid():
            updated = form.save()
            trigger_notifications(request.user, updated, old_status, old_deadline, old_interview)
            return redirect('application_list')
    else:
        form = JobApplicationForm(instance=app)
    return render(request, 'applications/form.html', {'form': form, 'action': 'Edit'})

@login_required
def application_delete(request, pk):
    app = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == 'POST':
        app.delete()
        return redirect('application_list')
    return render(request, 'applications/confirm_delete.html', {'app': app})

class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = JobApplication
    template_name = 'applications/detail.html'
    context_object_name = 'app'

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        try:
            from dashboard.views import track_recently_viewed
            track_recently_viewed(request, self.object.pk)
        except ImportError:
            pass
        return response


application_list = ApplicationListView.as_view()
application_detail = ApplicationDetailView.as_view()

def trigger_notifications(user, app, old_status, old_deadline, old_interview):
    # Import here to avoid circular import
    # Jaimil's Notification model lives in the dashboard app
    try:
        from dashboard.models import Notification
    except ImportError:
        return  # Dashboard not ready yet — skip silently

    if app.status != old_status:
        Notification.objects.create(
            user=user,
            message=f'Application for {app.job_title} at {app.company_name} changed to {app.status}.',
            type='status'
        )
    if app.interview_date and app.interview_date != old_interview:
        Notification.objects.create(
            user=user,
            message=f'Interview date updated for {app.job_title} at {app.company_name}: {app.interview_date}.',
            type='interview'
        )
    if app.deadline and app.deadline != old_deadline:
        Notification.objects.create(
            user=user,
            message=f'Deadline updated for {app.job_title} at {app.company_name}: {app.deadline}.',
            type='deadline'
        )
