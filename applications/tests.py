from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import JobApplication


class ApplicationSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student',
            password='test-password-123',
        )
        self.other_user = User.objects.create_user(
            username='other-student',
            password='test-password-123',
        )
        self.url = reverse('application_list')

    def create_application(self, **overrides):
        defaults = {
            'user': self.user,
            'company_name': 'Northwind Labs',
            'job_title': 'Software Intern',
            'job_location': 'Toronto',
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_search_matches_company_name(self):
        self.client.login(username='student', password='test-password-123')
        self.create_application(company_name='OpenAI')
        self.create_application(company_name='Contoso')

        response = self.client.get(self.url, {'q': 'open'})

        self.assertContains(response, 'OpenAI')
        self.assertNotContains(response, 'Contoso')
        self.assertEqual(response.context['search_query'], 'open')

    def test_search_matches_job_title(self):
        self.client.login(username='student', password='test-password-123')
        self.create_application(job_title='Data Analyst Intern')
        self.create_application(job_title='Marketing Intern')

        response = self.client.get(self.url, {'q': 'analyst'})

        self.assertContains(response, 'Data Analyst Intern')
        self.assertNotContains(response, 'Marketing Intern')

    def test_search_matches_location(self):
        self.client.login(username='student', password='test-password-123')
        self.create_application(job_location='Vancouver')
        self.create_application(job_location='Montreal')

        response = self.client.get(self.url, {'q': 'van'})

        self.assertContains(response, 'Vancouver')
        self.assertNotContains(response, 'Montreal')

    def test_empty_search_shows_all_user_applications(self):
        self.client.login(username='student', password='test-password-123')
        self.create_application(company_name='OpenAI')
        self.create_application(company_name='Contoso')

        response = self.client.get(self.url, {'q': '   '})

        self.assertContains(response, 'OpenAI')
        self.assertContains(response, 'Contoso')
        self.assertEqual(response.context['search_query'], '')

    def test_search_only_returns_current_user_applications(self):
        self.client.login(username='student', password='test-password-123')
        self.create_application(company_name='OpenAI')
        self.create_application(
            user=self.other_user,
            company_name='OpenAI Secret Role',
            job_title='Backend Intern',
        )

        response = self.client.get(self.url, {'q': 'openai'})

        self.assertContains(response, 'OpenAI')
        self.assertNotContains(response, 'OpenAI Secret Role')
