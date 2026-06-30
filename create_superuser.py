import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interntrack.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gmail.com', 'admin1234')
    print("Superuser 'admin' created successfully.")
else:
    print("Superuser 'admin' already exists.")
