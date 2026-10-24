from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.workstations.models import WorkstationControl

UserModel = get_user_model()


def start_workstation(port: str, user: UserModel | None = None) -> WorkstationControl:
    with transaction.atomic():
        control = WorkstationControl.objects.select_for_update().get(port=port)
        control.is_running = True
        control.last_started_by = user
        control.last_started_at = timezone.now()
        control.save(update_fields=["is_running", "last_started_by", "last_started_at", "updated_at"])
        return control


def stop_workstation(port: str, user: UserModel | None = None) -> WorkstationControl:
    with transaction.atomic():
        control = WorkstationControl.objects.select_for_update().get(port=port)
        control.is_running = False
        control.last_stopped_by = user
        control.last_stopped_at = timezone.now()
        control.save(update_fields=["is_running", "last_stopped_by", "last_stopped_at", "updated_at"])
        return control
