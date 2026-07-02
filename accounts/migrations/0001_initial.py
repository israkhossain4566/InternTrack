from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_missing_user_profiles(apps, schema_editor):
    user_app_label, user_model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(user_app_label, user_model_name)
    UserProfile = apps.get_model('accounts', 'UserProfile')

    existing_profile_user_ids = set(
        UserProfile.objects.values_list('user_id', flat=True)
    )
    missing_profiles = [
        UserProfile(user=user)
        for user in User.objects.exclude(id__in=existing_profile_user_ids)
    ]
    UserProfile.objects.bulk_create(missing_profiles)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(blank=True, max_length=255)),
                ('university', models.CharField(blank=True, max_length=255)),
                ('program', models.CharField(blank=True, max_length=255)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pictures/')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(create_missing_user_profiles, migrations.RunPython.noop),
    ]
