# PowerShell helper for Django checks.
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"
python .\manage.py check
