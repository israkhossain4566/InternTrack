import json
from collections import defaultdict

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from applications.models import JobApplication
from documents.models import UploadedDocument
from .models import Notification


# ---------------------------------------------------------------------------
# Helper: build chart data for the dashboard
# ---------------------------------------------------------------------------

def _build_chart_data(applications):
    """Return serialisable dicts for Chart.js."""

    # --- Status Distribution ---
    status_counts = defaultdict(int)
    for app in applications:
        status_counts[app.status] += 1

    status_labels = ['Saved', 'Applied', 'Interview', 'Offer', 'Rejected']
    status_data = [status_counts.get(s, 0) for s in status_labels]

    # --- Monthly Applications (current year) ---
    current_year = timezone.now().year
    monthly_counts = defaultdict(int)
    for app in applications:
        if app.application_date.year == current_year:
            monthly_counts[app.application_date.month] += 1

    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_data = [monthly_counts.get(m, 0) for m in range(1, 13)]

    # --- Offer Ratio (Offer vs Non-Offer) ---
    offer_count = status_counts.get('Offer', 0)
    non_offer_count = sum(v for k, v in status_counts.items() if k != 'Offer')

    return {
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'month_labels': json.dumps(month_labels),
        'monthly_data': json.dumps(monthly_data),
        'offer_data': json.dumps([offer_count, non_offer_count]),
        'offer_labels': json.dumps(['Offer', 'Other']),
    }


# ---------------------------------------------------------------------------
# Dashboard Home
# ---------------------------------------------------------------------------

@login_required
def dashboard_home(request):
    applications = JobApplication.objects.filter(user=request.user)

    # --- Stat counts ---
    stats = {
        'total': applications.count(),
        'saved': applications.filter(status='Saved').count(),
        'applied': applications.filter(status='Applied').count(),
        'interview': applications.filter(status='Interview').count(),
        'offer': applications.filter(status='Offer').count(),
        'rejected': applications.filter(status='Rejected').count(),
    }

    # --- Chart data ---
    chart_data = _build_chart_data(applications)

    # --- Session tracking ---
    # Last login (stored in session on each visit)
    last_login = request.session.get('last_login', None)
    request.session['last_login'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    # Recently viewed applications (store last 5 viewed PKs in session)
    recently_viewed_pks = request.session.get('recently_viewed', [])
    recently_viewed = []
    for pk in recently_viewed_pks:
        try:
            app = applications.get(pk=pk)
            recently_viewed.append(app)
        except JobApplication.DoesNotExist:
            pass

    # --- Cookie tracking ---
    # Daily visit count
    today_str = timezone.now().strftime('%Y-%m-%d')
    visit_date = request.COOKIES.get('visit_date', '')
    daily_visits = int(request.COOKIES.get('daily_visits', 0))

    if visit_date == today_str:
        daily_visits += 1
    else:
        daily_visits = 1

    # Most searched company
    most_searched_company = request.COOKIES.get('most_searched_company', 'N/A')

    context = {
        **stats,
        **chart_data,
        'last_login': last_login,
        'recently_viewed': recently_viewed,
        'daily_visits': daily_visits,
        'most_searched_company': most_searched_company,
    }

    response = render(request, 'dashboard/dashboard.html', context)
    response.set_cookie('visit_date', today_str, max_age=86400)
    response.set_cookie('daily_visits', daily_visits, max_age=86400)
    return response


# ---------------------------------------------------------------------------
# Recently Viewed Helper (called from applications views)
# ---------------------------------------------------------------------------

def track_recently_viewed(request, pk):
    """Add a job application PK to the recently-viewed session list."""
    viewed = request.session.get('recently_viewed', [])
    pk = int(pk)
    if pk in viewed:
        viewed.remove(pk)
    viewed.insert(0, pk)
    request.session['recently_viewed'] = viewed[:5]


# ---------------------------------------------------------------------------
# Notification Views
# ---------------------------------------------------------------------------

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    return render(request, 'dashboard/notifications.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
    })


@login_required
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('dashboard:notification_list')


@login_required
def notification_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('dashboard:notification_list')


@login_required
def notification_delete(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if request.method == 'POST':
        notification.delete()
    return redirect('dashboard:notification_list')


# ---------------------------------------------------------------------------
# Admin Statistics
# ---------------------------------------------------------------------------

@login_required
def notifications_api(request):
    """JSON endpoint for the navbar bell dropdown."""
    notifications = Notification.objects.filter(user=request.user)[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.pk,
                'message': n.message,
                'type': n.type,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%b %d, %Y %H:%M'),
            }
            for n in notifications
        ],
    }
    return JsonResponse(data)


@staff_member_required
def admin_stats(request):
    from applications.models import Company
    context = {
        'total_users': User.objects.count(),
        'total_companies': Company.objects.count(),
        'total_applications': JobApplication.objects.count(),
        'total_documents': UploadedDocument.objects.count(),
    }
    return render(request, 'dashboard/admin_stats.html', context)
