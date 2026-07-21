from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_notification_follow_up_application'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('follow_up', 'Follow-up Reminder'), ('interview', 'Interview Update'), ('deadline', 'Deadline Update'), ('new_application', 'New Application'), ('status_change', 'Status Change'), ('general', 'General')], default='general', max_length=20),
        ),
    ]