from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import JobApplication
from .models import Notification
from .services import (
    FOLLOW_UP_TYPE,
    complete_follow_up,
    create_due_follow_up_notifications,
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
