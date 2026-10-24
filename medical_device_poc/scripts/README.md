# Project Scripts

- `start_platform.ps1`: desktop-friendly launcher that starts Django, keeps the window open, and opens the browser automatically.
- `start_platform.cmd`: double-click wrapper for `start_platform.ps1`, suitable for a desktop shortcut.
- `create_desktop_shortcut.ps1`: create or refresh the desktop shortcut named `医用器械管理平台.lnk`.
- `runserver.ps1`: start local Django development server.
- `check.ps1`: run Django system checks.

Run scripts from the project root:

```powershell
cd D:\projects\CODEX开发\medical_device_poc
.\scripts\check.ps1
```

To start the platform from a terminal, use the same wrapper as the desktop shortcut:

```powershell
.\scripts\start_platform.cmd
```

To create or refresh the desktop shortcut:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_desktop_shortcut.ps1
```

The desktop shortcut points to:

```text
D:\projects\CODEX开发\medical_device_poc\scripts\start_platform.cmd
```

Keep the launcher window open while using the platform. Closing the window stops Django and the automatic submission processor.

## Docker services

The Docker Compose setup does not use the desktop launcher or Django `runserver` auto-thread. It runs two separate Django containers:

- `web`: serves Django through Gunicorn.
- `worker`: runs `python manage.py process_submissions` continuously.

This keeps the web process and A/B submission processor independently restartable for local cloud-style validation.

For local Docker checks, verify both the page and collected static CSS:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/ -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/static/css/app.css -UseBasicParsing
```
