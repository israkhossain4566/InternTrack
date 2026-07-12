from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Company, JobApplication
from .forms import JobApplicationForm, CompanyForm

@login_required
def application_list(request):
    applications = JobApplication.objects.filter(user=request.user)
    search_query = request.GET.get('q', '').strip()

    if search_query:
        applications = applications.filter(
            Q(company_name__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(job_location__icontains=search_query)
        )

    return render(request, 'applications/list.html', {
        'applications': applications,
        'search_query': search_query,
    })

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
