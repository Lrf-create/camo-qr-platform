from __future__ import annotations

from django.conf import settings
from django.db import models


class WorkstationControl(models.Model):
    class Port(models.TextChoices):
        A = "A", "A口"
        B = "B", "B口"

    port = models.CharField(max_length=1, choices=Port.choices, unique=True)
    is_running = models.BooleanField(default=False)
    last_started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_workstations",
    )
    last_stopped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stopped_workstations",
    )
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_stopped_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workstation_control"
        ordering = ["port"]
