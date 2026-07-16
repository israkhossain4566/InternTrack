from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        ('follow_up', 'Follow-up Reminder'),
        ('interview', 'Interview Update'),
        ('deadline', 'Deadline Update'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    application = models.ForeignKey(
        'applications.JobApplication',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.user.username}: {self.message[:50]}"
