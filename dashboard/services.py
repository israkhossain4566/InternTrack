import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from applications.models import JobApplication
from .emails import send_notification_email
from .models import Notification

logger = logging.getLogger(__name__)


FOLLOW_UP_TYPE = 'follow_up'
NEW_APPLICATION_TYPE = 'new_application'
STATUS_CHANGE_TYPE = 'status_change'
INTERVIEW_TYPE = 'interview'

# Notification types that are also emailed to the user, per the task brief.
# 'deadline' and 'general' are left out for now: nothing currently creates
# 'deadline'-typed notifications, and 'general' is a catch-all that isn't
# necessarily worth an inbox interruption.
EMAIL_WORTHY_TYPES = {
    NEW_APPLICATION_TYPE,
    STATUS_CHANGE_TYPE,
    INTERVIEW_TYPE,
    FOLLOW_UP_TYPE,
}


def _create_and_maybe_email(**kwargs):
    """Create a Notification and, if its type is email-worthy, email it.

    This is the single hook-in point for notification creation used by every
    function below. Email failures are caught and logged here so they can
    never break the in-app notification (or whatever user action triggered
    it) -- the Notification row is always committed first.
    """
    notification = Notification.objects.create(**kwargs)

    if notification.type in EMAIL_WORTHY_TYPES:
        try:
            send_notification_email(notification.user, notification)
        except Exception:
            logger.exception(
                "Failed to send notification email for notification id=%s",
                notification.pk,
            )

    return notification


def follow_up_message(application):
    role = f"{application.job_title} at {application.company_name}"

    if application.status == 'Saved':
        return f"Review your saved application for {role} and decide the next step."
    if application.status == 'Interview':
        return f"Check in on your interview process for {role}."
    if application.status == 'Offer':
        return f"Review the offer details and next deadline for {role}."
    return f"Follow up on your application for {role}."


def create_new_application_notification(application):
    """Create a one-time notification when an application is first added.

    Guarded so it can never fire twice for the same application, even if
    this is accidentally called more than once for the same object.
    """
    already_exists = Notification.objects.filter(
        application=application,
        type=NEW_APPLICATION_TYPE,
    ).exists()
    if already_exists:
        return None

    role = f"{application.job_title} at {application.company_name}"
    return _create_and_maybe_email(
        user=application.user,
        application=application,
        message=f"New application added: {role}.",
        type=NEW_APPLICATION_TYPE,
    )


def create_status_change_notification(application, previous_status):
    """Create a notification when an application's status actually changes.

    Callers should only invoke this when previous_status != application.status;
    that comparison is the dedup guard for repeated edits that don't change
    status (e.g. re-saving the same form).
    """
    if previous_status == application.status:
        return None

    role = f"{application.job_title} at {application.company_name}"
    return _create_and_maybe_email(
        user=application.user,
        application=application,
        message=f"Status update for {role}: {previous_status} -> {application.status}.",
        type=STATUS_CHANGE_TYPE,
    )


def create_interview_update_notification(application, previous_interview_date):
    """Create a notification when an interview is newly scheduled or moved.

    Fires only when the application is in (or moving into) 'Interview' status
    and the interview_date actually changed, so unrelated edits to the same
    application don't create duplicate interview notifications.
    """
    if application.status != 'Interview':
        return None
    if application.interview_date is None:
        return None
    if previous_interview_date == application.interview_date:
        return None

    role = f"{application.job_title} at {application.company_name}"
    if previous_interview_date is None:
        message = (
            f"Interview scheduled for {role} on "
            f"{application.interview_date.strftime('%b %d, %Y')}."
        )
    else:
        message = (
            f"Interview for {role} moved to "
            f"{application.interview_date.strftime('%b %d, %Y')}."
        )

    return _create_and_maybe_email(
        user=application.user,
        application=application,
        message=message,
        type=INTERVIEW_TYPE,
    )


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

            _create_and_maybe_email(
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