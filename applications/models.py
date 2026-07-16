from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Company(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class JobApplication(models.Model):
    DEFAULT_FOLLOW_UP_INTERVAL_DAYS = 7
    FINAL_STATUSES = {'Rejected'}

    STATUS_CHOICES = [
        ('Saved', 'Saved'),
        ('Applied', 'Applied'),
        ('Interview', 'Interview'),
        ('Offer', 'Offer'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)  # simple text now
    job_title = models.CharField(max_length=200)
    job_location = models.CharField(max_length=200, blank=True)
    internship_type = models.CharField(max_length=100, blank=True)
    application_date = models.DateField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Saved')
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    interview_date = models.DateField(null=True, blank=True)
    follow_up_due_date = models.DateField(null=True, blank=True)
    follow_up_interval_days = models.PositiveSmallIntegerField(default=DEFAULT_FOLLOW_UP_INTERVAL_DAYS)
    last_follow_up_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

    @property
    def needs_follow_up(self):
        return self.status not in self.FINAL_STATUSES

    def schedule_follow_up(self, reference_date=None):
        if not self.needs_follow_up:
            self.clear_follow_up()
            return

        reference_date = reference_date or timezone.localdate()
        self.follow_up_due_date = reference_date + timedelta(days=self.follow_up_interval_days)
        self.last_follow_up_sent_at = None

    def clear_follow_up(self):
        self.follow_up_due_date = None
        self.last_follow_up_sent_at = None
