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

    def test_add_application_schedules_default_follow_up_without_notification(self):
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
        self.assertFalse(Notification.objects.filter(user=self.user).exists())

    def test_edit_application_status_reschedules_without_status_notification(self):
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
        self.assertFalse(Notification.objects.filter(user=self.user, type='status').exists())
