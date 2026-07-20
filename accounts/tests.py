from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class PasswordResetEmailTests(TestCase):
    """Test suite for password reset email functionality"""
    
    def setUp(self):
        """Set up test client and test user"""
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='oldpassword123'
        )
        self.password_reset_url = reverse('password_reset')
        self.password_reset_done_url = reverse('password_reset_done')
        
    def test_password_reset_page_loads(self):
        """Test that password reset form page loads successfully"""
        response = self.client.get(self.password_reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset Password')
        self.assertContains(response, 'email')
        
    def test_password_reset_sends_email(self):
        """Test that password reset sends an email with valid user email"""
        # Clear any existing emails
        mail.outbox = []
        
        # Submit password reset form
        response = self.client.post(self.password_reset_url, {
            'email': self.test_user.email
        })
        
        # Check redirect to done page
        self.assertRedirects(response, self.password_reset_done_url)
        
        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn(self.test_user.email, email.to)
        self.assertIn('password reset', email.subject.lower())
        self.assertIn('reset', email.body.lower())
        
    def test_password_reset_email_contains_reset_link(self):
        """Test that password reset email contains a valid reset link"""
        mail.outbox = []
        
        # Submit password reset form
        self.client.post(self.password_reset_url, {
            'email': self.test_user.email
        })
        
        # Get the email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Check that email body contains a reset link
        # The link should contain uidb64 and token
        self.assertIn('/reset/', email.body)
        
    def test_password_reset_with_nonexistent_email(self):
        """Test password reset with non-existent email (should not send email for security)"""
        mail.outbox = []
        
        # Submit with non-existent email
        response = self.client.post(self.password_reset_url, {
            'email': 'nonexistent@example.com'
        })
        
        # Should still redirect to done page (security measure)
        self.assertRedirects(response, self.password_reset_done_url)
        
        # But no email should be sent
        self.assertEqual(len(mail.outbox), 0)
        
    def test_password_reset_with_invalid_email_format(self):
        """Test password reset with invalid email format"""
        response = self.client.post(self.password_reset_url, {
            'email': 'invalid-email-format'
        })
        
        # Should show form with error (not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')
        
    def test_password_reset_confirm_page_loads(self):
        """Test that password reset confirm page loads with valid token"""
        # Generate valid token and uidb64
        token = default_token_generator.make_token(self.test_user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        # Access the confirm page
        url = reverse('password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        })
        response = self.client.get(url)
        
        # Should redirect to set-password page (Django's default behavior)
        self.assertEqual(response.status_code, 302)
        
    def test_password_reset_confirm_with_invalid_token(self):
        """Test password reset confirm with invalid token"""
        uidb64 = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        # Use invalid token
        url = reverse('password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': 'invalid-token-xxx'
        })
        response = self.client.get(url)
        
        # Should show error page
        self.assertEqual(response.status_code, 200)
        # Check for invalid token message (case insensitive check)
        response_text = response.content.decode('utf-8').lower()
        self.assertIn('invalid', response_text)
        
    def test_complete_password_reset_flow(self):
        """Test the complete password reset flow from email to new password"""
        mail.outbox = []
        
        # Step 1: Request password reset
        self.client.post(self.password_reset_url, {
            'email': self.test_user.email
        })
        
        # Step 2: Extract token from email
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        
        # Generate valid token and uidb64 (simulating email link)
        token = default_token_generator.make_token(self.test_user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        # Step 3: Access reset confirm page
        confirm_url = reverse('password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        })
        response = self.client.get(confirm_url, follow=True)
        
        # Step 4: Submit new password
        new_password = 'newpassword456'
        response = self.client.post(response.request['PATH_INFO'], {
            'new_password1': new_password,
            'new_password2': new_password,
        }, follow=True)
        
        # Step 5: Verify password was changed
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.check_password(new_password))
        
        # Step 6: Verify old password no longer works
        self.assertFalse(self.test_user.check_password('oldpassword123'))
        
    def test_password_reset_complete_page_loads(self):
        """Test that password reset complete page loads"""
        url = reverse('password_reset_complete')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for password-related content (case insensitive check)
        response_text = response.content.decode('utf-8').lower()
        self.assertIn('password', response_text)


class EmailConfigurationTests(TestCase):
    """Test suite to verify email configuration"""
    
    def test_email_backend_configured(self):
        """Test that email backend is properly configured"""
        from django.conf import settings
        
        # Check that email backend is set
        self.assertIsNotNone(settings.EMAIL_BACKEND)
        self.assertIn('mail.backends', settings.EMAIL_BACKEND)
        
    def test_email_host_configured(self):
        """Test that email host is configured"""
        from django.conf import settings
        
        self.assertIsNotNone(settings.EMAIL_HOST)
        
    def test_email_port_configured(self):
        """Test that email port is configured"""
        from django.conf import settings
        
        self.assertIsNotNone(settings.EMAIL_PORT)
        self.assertIsInstance(settings.EMAIL_PORT, int)
        
    def test_default_from_email_configured(self):
        """Test that default from email is configured"""
        from django.conf import settings
        
        self.assertIsNotNone(settings.DEFAULT_FROM_EMAIL)
