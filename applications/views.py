from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
from .models import Company, JobApplication
from .forms import JobApplicationForm, CompanyForm

@login_required
def application_list(request):
    user_applications = JobApplication.objects.filter(user=request.user)
    applications = user_applications
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    company_filter = request.GET.get('company', '').strip()
    internship_type_filter = request.GET.get('internship_type', '').strip()
    deadline_filter = request.GET.get('deadline', '').strip()
    date_applied_filter = request.GET.get('date_applied', '').strip()
    sort_filter = request.GET.get('sort', '').strip()
    direction_filter = request.GET.get('direction', 'asc').strip()

    if search_query:
        applications = applications.filter(
            Q(company_name__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(job_location__icontains=search_query)
        )

    if status_filter:
        applications = applications.filter(status=status_filter)

    if company_filter:
        applications = applications.filter(company_name=company_filter)

    if internship_type_filter:
        applications = applications.filter(internship_type=internship_type_filter)

    if deadline_filter:
        deadline_date = parse_date(deadline_filter)
        if deadline_date:
            applications = applications.filter(deadline=deadline_date)

    if date_applied_filter:
        application_date = parse_date(date_applied_filter)
        if application_date:
            applications = applications.filter(application_date=application_date)

    company_options = user_applications.exclude(company_name='').order_by(
        'company_name'
    ).values_list('company_name', flat=True).distinct()
    internship_type_options = user_applications.exclude(internship_type='').order_by(
        'internship_type'
    ).values_list('internship_type', flat=True).distinct()
    filters_active = any([
        status_filter,
        company_filter,
        internship_type_filter,
        deadline_filter,
        date_applied_filter,
    ])
    sort_options = [
        ('company_name', 'Company'),
        ('status', 'Status'),
        ('deadline', 'Deadline'),
        ('application_date', 'Application Date'),
    ]
    sort_fields = {value: value for value, label in sort_options}
    sort_field = sort_fields.get(sort_filter)
    sort_direction = 'desc' if direction_filter == 'desc' else 'asc'

    if sort_field:
        order_field = f'-{sort_field}' if sort_direction == 'desc' else sort_field
        applications = applications.order_by(order_field, 'id')
    else:
        applications = applications.order_by('id')

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()
    paginator = Paginator(applications, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'applications': page_obj.object_list,
        'page_obj': page_obj,
        'query_string': query_string,
        'search_query': search_query,
        'status_choices': JobApplication.STATUS_CHOICES,
        'company_options': company_options,
        'internship_type_options': internship_type_options,
        'status_filter': status_filter,
        'company_filter': company_filter,
        'internship_type_filter': internship_type_filter,
        'deadline_filter': deadline_filter,
        'date_applied_filter': date_applied_filter,
        'sort_options': sort_options,
        'sort_filter': sort_filter,
        'direction_filter': sort_direction,
        'filters_active': filters_active,
        'search_or_filters_active': bool(search_query or filters_active or sort_field),
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'applications/_application_results.html', context)

    return render(request, 'applications/list.html', context)

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

@login_required
def application_detail(request, pk):
    app = get_object_or_404(JobApplication, pk=pk, user=request.user)
    # Track recently viewed in session (dashboard feature)
    try:
        from dashboard.views import track_recently_viewed
        track_recently_viewed(request, pk)
    except ImportError:
        pass
    return render(request, 'applications/detail.html', {'app': app})

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
