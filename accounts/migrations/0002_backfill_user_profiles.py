from django.conf import settings
from django.db import migrations


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

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_missing_user_profiles, migrations.RunPython.noop),
    ]
