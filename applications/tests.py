from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Notification
from .models import JobApplication


class ApplicationReminderSchedulingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='pass')
        self.client.force_login(self.user)

    def test_add_application_schedules_default_follow_up_and_new_application_notification(self):
        response = self.client.post(reverse('application_add'), {
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'job_location': 'Remote',
            'internship_type': 'Summer',
            'deadline': '',
            'status': 'Applied',
            'salary': '',
            'notes': '',
            'interview_date': '',
            'follow_up_interval_days': 7,
        })

        application = JobApplication.objects.get(user=self.user)
        self.assertRedirects(response, reverse('application_list'))
        self.assertEqual(application.follow_up_due_date, timezone.localdate() + timedelta(days=7))

        new_application_notifications = Notification.objects.filter(
            user=self.user, application=application, type='new_application',
        )
        self.assertEqual(new_application_notifications.count(), 1)
        self.assertIn('New application added', new_application_notifications.first().message)
        # Adding never creates a status_change notification (there's no "previous" status).
        self.assertFalse(Notification.objects.filter(user=self.user, type='status_change').exists())

    def test_edit_application_status_reschedules_and_creates_status_change_notification(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name='Acme',
            job_title='Software Intern',
            status='Saved',
            follow_up_due_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.post(reverse('application_edit', args=[application.pk]), {
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'job_location': '',
            'internship_type': '',
            'deadline': '',
            'status': 'Applied',
            'salary': '',
            'notes': '',
            'interview_date': '',
            'follow_up_interval_days': 7,
        })

        application.refresh_from_db()
        self.assertRedirects(response, reverse('application_list'))
        self.assertEqual(application.follow_up_due_date, timezone.localdate() + timedelta(days=7))

        status_notifications = Notification.objects.filter(
            user=self.user, application=application, type='status_change',
        )
        self.assertEqual(status_notifications.count(), 1)
        self.assertIn('Saved -> Applied', status_notifications.first().message)

    def test_editing_without_changing_status_does_not_duplicate_status_notification(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name='Acme',
            job_title='Software Intern',
            status='Applied',
            follow_up_due_date=timezone.localdate() - timedelta(days=1),
        )

        post_data = {
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'job_location': '',
            'internship_type': '',
            'deadline': '',
            'status': 'Applied',
            'salary': '',
            'notes': 'Updated notes only',
            'interview_date': '',
            'follow_up_interval_days': 7,
        }

        # Save twice with the same status; neither save should create a
        # status_change notification since the status never actually changes.
        self.client.post(reverse('application_edit', args=[application.pk]), post_data)
        self.client.post(reverse('application_edit', args=[application.pk]), post_data)

        self.assertFalse(
            Notification.objects.filter(
                user=self.user, application=application, type='status_change',
            ).exists()
        )

    def test_moving_to_interview_status_with_date_creates_interview_notification(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name='Acme',
            job_title='Software Intern',
            status='Applied',
        )
        interview_date = timezone.localdate() + timedelta(days=5)

        response = self.client.post(reverse('application_edit', args=[application.pk]), {
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'job_location': '',
            'internship_type': '',
            'deadline': '',
            'status': 'Interview',
            'salary': '',
            'notes': '',
            'interview_date': interview_date.isoformat(),
            'follow_up_interval_days': 7,
        })

        self.assertRedirects(response, reverse('application_list'))
        interview_notifications = Notification.objects.filter(
            user=self.user, application=application, type='interview',
        )
        self.assertEqual(interview_notifications.count(), 1)
        self.assertIn('Interview scheduled', interview_notifications.first().message)

    def test_resaving_same_interview_date_does_not_duplicate_interview_notification(self):
        interview_date = timezone.localdate() + timedelta(days=5)
        application = JobApplication.objects.create(
            user=self.user,
            company_name='Acme',
            job_title='Software Intern',
            status='Interview',
            interview_date=interview_date,
        )

        post_data = {
            'company_name': 'Acme',
            'job_title': 'Software Intern',
            'job_location': '',
            'internship_type': '',
            'deadline': '',
            'status': 'Interview',
            'salary': '',
            'notes': 'Same interview date, just fixing a typo in notes',
            'interview_date': interview_date.isoformat(),
            'follow_up_interval_days': 7,
        }

        self.client.post(reverse('application_edit', args=[application.pk]), post_data)
        self.client.post(reverse('application_edit', args=[application.pk]), post_data)

        self.assertFalse(
            Notification.objects.filter(
                user=self.user, application=application, type='interview',
            ).exists()
        )