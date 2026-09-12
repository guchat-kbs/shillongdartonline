```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

python manage.py shell -c "
from django.contrib.auth import get_user_model

User = get_user_model()

username = 'sakal'
email = 'sakalytshit@gmail.com'
password = 'Salibill1'

if User.objects.filter(username=username).exists():
    print('Superbase already there')
else:
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
    )
    print('Superuser sakal created successfully.')
"

python manage.py shell -c "
from entries.models import Entry

deleted_count = Entry.objects.filter(owner__isnull=True).count()
print(f'Deleting {deleted_count} orphaned entries...')
Entry.objects.filter(owner__isnull=True).delete()
"
```
