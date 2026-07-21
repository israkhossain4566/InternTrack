from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.generic import DetailView, ListView

from .forms import JobApplicationForm
from .models import JobApplication


class ApplicationListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'applications/list.html'
    context_object_name = 'applications'
    paginate_by = 10
    sort_options = [
        ('company_name', 'Company'),
        ('status', 'Status'),
        ('deadline', 'Deadline'),
        ('application_date', 'Application Date'),
    ]

    def dispatch(self, request, *args, **kwargs):
        self.search_query = request.GET.get('q', '').strip()
        self.status_filter = request.GET.get('status', '').strip()
        self.company_filter = request.GET.get('company', '').strip()
        self.internship_type_filter = request.GET.get('internship_type', '').strip()
        self.deadline_filter = request.GET.get('deadline', '').strip()
        self.date_applied_filter = request.GET.get('date_applied', '').strip()
        self.sort_filter = request.GET.get('sort', '').strip()
        self.direction_filter = request.GET.get('direction', 'asc').strip()
        self.sort_direction = 'desc' if self.direction_filter == 'desc' else 'asc'
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

        sort_fields = {value: value for value, label in self.sort_options}
        self.sort_field = sort_fields.get(self.sort_filter)

        if self.sort_field:
            order_field = f'-{self.sort_field}' if self.sort_direction == 'desc' else self.sort_field
            applications = applications.order_by(order_field, 'id')
        else:
            applications = applications.order_by('id')

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
        query_params = self.request.GET.copy()
        query_params.pop('page', None)

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
            'sort_options': self.sort_options,
            'sort_filter': self.sort_filter,
            'direction_filter': self.sort_direction,
            'query_string': query_params.urlencode(),
            'filters_active': filters_active,
            'search_or_filters_active': bool(self.search_query or filters_active or self.sort_field),
        })
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            response = render(self.request, 'applications/_application_results.html', context)
        else:
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
            trigger_notifications(app, is_new=True)
            return redirect('application_list')
    else:
        form = JobApplicationForm()
    return render(request, 'applications/form.html', {'form': form, 'action': 'Add'})


@login_required
def application_edit(request, pk):
    app = get_object_or_404(JobApplication, pk=pk, user=request.user)

    if request.method == 'POST':
        # Snapshot the fields we need to diff *before* the form overwrites them,
        # so we can tell whether status/interview_date actually changed and
        # avoid firing duplicate notifications on no-op edits.
        previous_status = app.status
        previous_interview_date = app.interview_date

        form = JobApplicationForm(request.POST, instance=app)
        if form.is_valid():
            updated = form.save()
            trigger_notifications(
                updated,
                is_new=False,
                previous_status=previous_status,
                previous_interview_date=previous_interview_date,
            )
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


def trigger_notifications(app, is_new=False, previous_status=None, previous_interview_date=None):
    """Create/update notifications for an application add or edit.

    - Always resyncs the follow-up reminder schedule (existing behavior).
    - Creates an 'interview' notification only if the interview date actually
      changed while the application is in 'Interview' status.

    'new_application' and 'status_change' notifications are intentionally
    NOT created here: they fired for edits the user just made themselves,
    which felt like noise (you don't need to be notified about your own
    action). Follow-up and interview reminders stay, since those surface
    something the user asked to be reminded about later, not something they
    just did. The underlying create_new_application_notification() and
    create_status_change_notification() helpers are left in
    dashboard/services.py, unused, in case this needs to be reintroduced
    (e.g. behind a user preference) later.

    Each helper below has its own dedup guard, so calling this multiple times
    for the same edit (e.g. a form resubmit) will not create duplicates.
    """
    try:
        from dashboard.services import (
            create_interview_update_notification,
            sync_application_follow_up,
        )
    except ImportError:
        return

    sync_application_follow_up(app)

    if is_new:
        return

    create_interview_update_notification(app, previous_interview_date)