"""Email delivery for dashboard notifications.

This module is intentionally small and built directly on Django's own mail
utilities (django.core.mail.send_mail) rather than a custom mail system, so
it automatically respects whatever EMAIL_BACKEND / SMTP settings are
configured in interntrack/settings.py (console backend in dev, real SMTP in
production).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


# Human-friendly subject prefixes per notification type. Falls back to the
# notification's own get_type_display() for any type not listed here.
_SUBJECT_PREFIXES = {
    'new_application': 'New Application Added',
    'status_change': 'Application Status Update',
    'interview': 'Interview Update',
    'follow_up': 'Follow-up Reminder',
    'deadline': 'Deadline Update',
}


def send_notification_email(user, notification):
    """Email a single Notification to its owning user.

    Returns True if an email was handed off to Django's mail backend, False
    if sending was skipped (e.g. the user has no email on file). Any error
    raised by the mail backend (SMTP failures, auth errors, etc.) is allowed
    to propagate to the caller, which is responsible for deciding whether a
    failure should be swallowed -- see
    dashboard.services._create_and_maybe_email, which never lets an email
    failure block notification creation or the user action that triggered
    it.
    """
    recipient_email = getattr(user, 'email', '') or ''
    if not recipient_email.strip():
        logger.warning(
            "Skipping notification email for user id=%s: no email on file",
            getattr(user, 'pk', None),
        )
        return False

    subject_prefix = _SUBJECT_PREFIXES.get(
        notification.type, notification.get_type_display()
    )
    subject = f"InternTrack: {subject_prefix}"

    greeting_name = user.first_name or user.username
    body_lines = [
        f"Hi {greeting_name},",
        "",
        notification.message,
        "",
        "Log in to InternTrack to view more details.",
    ]
    message = "\n".join(body_lines)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )
    return True