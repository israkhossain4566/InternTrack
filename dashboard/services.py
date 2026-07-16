from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from applications.models import JobApplication
from .models import Notification


FOLLOW_UP_TYPE = 'follow_up'


def follow_up_message(application):
    role = f"{application.job_title} at {application.company_name}"

    if application.status == 'Saved':
        return f"Review your saved application for {role} and decide the next step."
    if application.status == 'Interview':
        return f"Check in on your interview process for {role}."
    if application.status == 'Offer':
        return f"Review the offer details and next deadline for {role}."
    return f"Follow up on your application for {role}."


def clear_pending_follow_up_notifications(application):
    Notification.objects.filter(
        application=application,
        type=FOLLOW_UP_TYPE,
        is_read=False,
    ).delete()


def sync_application_follow_up(application, reference_date=None):
    if application.needs_follow_up:
        application.schedule_follow_up(reference_date=reference_date)
    else:
        application.clear_follow_up()

    application.save(update_fields=[
        'follow_up_due_date',
        'last_follow_up_sent_at',
        'follow_up_interval_days',
    ])
    clear_pending_follow_up_notifications(application)


def create_due_follow_up_notifications(user):
    today = timezone.localdate()
    now = timezone.now()
    applications = JobApplication.objects.filter(
        user=user,
        follow_up_due_date__isnull=False,
        follow_up_due_date__lte=today,
    ).exclude(status__in=JobApplication.FINAL_STATUSES)

    created_count = 0
    with transaction.atomic():
        for application in applications.select_for_update():
            if (
                application.last_follow_up_sent_at
                and application.last_follow_up_sent_at.date() >= application.follow_up_due_date
            ):
                continue

            already_unread = Notification.objects.filter(
                user=user,
                application=application,
                type=FOLLOW_UP_TYPE,
                is_read=False,
            ).exists()
            if already_unread:
                continue

            Notification.objects.create(
                user=user,
                application=application,
                message=follow_up_message(application),
                type=FOLLOW_UP_TYPE,
            )
            application.last_follow_up_sent_at = now
            application.save(update_fields=['last_follow_up_sent_at'])
            created_count += 1

    return created_count


def complete_follow_up(notification, reference_date=None):
    application = notification.application
    if application:
        if application.needs_follow_up:
            application.schedule_follow_up(reference_date=reference_date)
        else:
            application.clear_follow_up()
        application.save(update_fields=['follow_up_due_date', 'last_follow_up_sent_at'])

    Notification.objects.filter(
        user=notification.user,
        application=application,
        type=FOLLOW_UP_TYPE,
        is_read=False,
    ).update(is_read=True)


def snooze_follow_up(notification, days=7):
    application = notification.application
    if application:
        application.follow_up_due_date = timezone.localdate() + timedelta(days=days)
        application.last_follow_up_sent_at = None
        application.save(update_fields=['follow_up_due_date', 'last_follow_up_sent_at'])

    Notification.objects.filter(
        user=notification.user,
        application=application,
        type=FOLLOW_UP_TYPE,
        is_read=False,
    ).update(is_read=True)
