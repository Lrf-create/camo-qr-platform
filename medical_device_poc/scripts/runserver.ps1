# PowerShell helper for local development.
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"
python .\manage.py runserver 127.0.0.1:8000
