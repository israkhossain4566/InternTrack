from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import JobApplication
from .emails import send_notification_email
from .models import Notification
from .services import (
    FOLLOW_UP_TYPE,
    INTERVIEW_TYPE,
    NEW_APPLICATION_TYPE,
    STATUS_CHANGE_TYPE,
    complete_follow_up,
    create_due_follow_up_notifications,
    create_interview_update_notification,
    create_new_application_notification,
    create_status_change_notification,
    snooze_follow_up,
    sync_application_follow_up,
)


class FollowUpReminderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass')

    def make_application(self, **overrides):
        data = {
            'user': self.user,
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'status': 'Applied',
            'follow_up_due_date': timezone.localdate() - timedelta(days=1),
        }
        data.update(overrides)
        return JobApplication.objects.create(**data)

    def test_due_follow_up_notification_is_created_once(self):
        application = self.make_application()

        created = create_due_follow_up_notifications(self.user)
        created_again = create_due_follow_up_notifications(self.user)

        notification = Notification.objects.get(application=application)
        self.assertEqual(created, 1)
        self.assertEqual(created_again, 0)
        self.assertEqual(notification.type, FOLLOW_UP_TYPE)
        self.assertFalse(notification.is_read)
        self.assertIn('Follow up on your application', notification.message)

    def test_completed_follow_up_marks_read_and_reschedules_application(self):
        application = self.make_application()
        create_due_follow_up_notifications(self.user)
        notification = Notification.objects.get(application=application)
        today = timezone.localdate()

        complete_follow_up(notification, reference_date=today)

        notification.refresh_from_db()
        application.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(application.follow_up_due_date, today + timedelta(days=7))
        self.assertIsNone(application.last_follow_up_sent_at)

    def test_snoozed_follow_up_marks_read_and_moves_due_date(self):
        application = self.make_application()
        create_due_follow_up_notifications(self.user)
        notification = Notification.objects.get(application=application)

        snooze_follow_up(notification, days=7)

        notification.refresh_from_db()
        application.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(application.follow_up_due_date, timezone.localdate() + timedelta(days=7))
        self.assertIsNone(application.last_follow_up_sent_at)

    def test_rejected_application_has_no_pending_follow_up(self):
        application = self.make_application(status='Rejected')
        Notification.objects.create(
            user=self.user,
            application=application,
            message='Old follow-up',
            type=FOLLOW_UP_TYPE,
        )

        sync_application_follow_up(application)
        created = create_due_follow_up_notifications(self.user)

        application.refresh_from_db()
        self.assertEqual(created, 0)
        self.assertIsNone(application.follow_up_due_date)
        self.assertFalse(Notification.objects.filter(application=application, is_read=False).exists())


class NotificationVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass')
        self.client.force_login(self.user)

    def test_default_notification_page_hides_read_notifications(self):
        Notification.objects.create(
            user=self.user,
            message='Already handled',
            type='general',
            is_read=True,
        )
        unread = Notification.objects.create(
            user=self.user,
            message='Needs attention',
            type='general',
        )

        response = self.client.get(reverse('dashboard:notification_list'))

        self.assertContains(response, unread.message)
        self.assertNotContains(response, 'Already handled')

    def test_history_mode_shows_read_notifications(self):
        read = Notification.objects.create(
            user=self.user,
            message='Already handled',
            type='general',
            is_read=True,
        )

        response = self.client.get(f"{reverse('dashboard:notification_list')}?show=history")

        self.assertContains(response, read.message)
        self.assertContains(response, 'Notification History')

    def test_dropdown_api_returns_only_unread_notifications(self):
        Notification.objects.create(
            user=self.user,
            message='Already handled',
            type='general',
            is_read=True,
        )
        Notification.objects.create(
            user=self.user,
            message='Needs attention',
            type='general',
        )

        response = self.client.get(reverse('dashboard:notifications_api'))
        messages = [item['message'] for item in response.json()['notifications']]

        self.assertEqual(messages, ['Needs attention'])


class NotificationEmailTests(TestCase):
    """Covers Jaimil's notification-email-delivery scope.

    Uses Django's locmem test email backend (the default under TestCase),
    so these assert against django.core.mail.outbox instead of hitting a
    real SMTP server.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='student',
            password='pass',
            email='student@example.com',
        )

    def make_application(self, **overrides):
        data = {
            'user': self.user,
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'status': 'Applied',
        }
        data.update(overrides)
        return JobApplication.objects.create(**data)

    def test_send_notification_email_delivers_to_user_address(self):
        notification = Notification.objects.create(
            user=self.user,
            message='New application added: Software Intern at Acme.',
            type=NEW_APPLICATION_TYPE,
        )

        sent = send_notification_email(self.user, notification)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['student@example.com'])
        self.assertIn('New Application Added', email.subject)
        self.assertIn(notification.message, email.body)

    def test_send_notification_email_skipped_when_user_has_no_email(self):
        user_without_email = User.objects.create_user(username='noemail', password='pass')
        notification = Notification.objects.create(
            user=user_without_email,
            message='Some update',
            type=NEW_APPLICATION_TYPE,
        )

        sent = send_notification_email(user_without_email, notification)

        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)

    def test_new_application_notification_sends_email(self):
        application = self.make_application()

        create_new_application_notification(application)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New Application Added', mail.outbox[0].subject)

    def test_status_change_notification_sends_email(self):
        application = self.make_application(status='Interview')

        create_status_change_notification(application, previous_status='Applied')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Application Status Update', mail.outbox[0].subject)

    def test_interview_notification_sends_email(self):
        interview_date = timezone.localdate() + timedelta(days=3)
        application = self.make_application(
            status='Interview',
            interview_date=interview_date,
        )

        create_interview_update_notification(application, previous_interview_date=None)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Interview Update', mail.outbox[0].subject)

    def test_due_follow_up_notification_sends_email(self):
        application = self.make_application(
            follow_up_due_date=timezone.localdate() - timedelta(days=1),
        )

        create_due_follow_up_notifications(self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Follow-up Reminder', mail.outbox[0].subject)

    def test_general_notification_does_not_send_email(self):
        Notification.objects.create(
            user=self.user,
            message='Just an FYI',
            type='general',
        )

        self.assertEqual(len(mail.outbox), 0)

    def test_notification_still_created_when_email_backend_fails(self):
        application = self.make_application()

        with patch('dashboard.services.send_notification_email', side_effect=RuntimeError('SMTP down')):
            notification = create_new_application_notification(application)

        self.assertIsNotNone(notification)
        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_repeated_edit_without_status_change_sends_no_extra_email(self):
        application = self.make_application(status='Applied')
        mail.outbox.clear()

        result = create_status_change_notification(application, previous_status='Applied')

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)