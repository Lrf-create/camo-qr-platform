from __future__ import annotations

from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.submissions"

    def ready(self) -> None:
        from apps.submissions.auto_processor import start_auto_processor

        start_auto_processor()
