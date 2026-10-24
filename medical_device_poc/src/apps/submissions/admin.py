from __future__ import annotations

from django.contrib import admin

from .models import PortASubmission, PortASubmissionItem, PortBSubmission, PortBSubmissionItem

admin.site.register(PortASubmission)
admin.site.register(PortASubmissionItem)
admin.site.register(PortBSubmission)
admin.site.register(PortBSubmissionItem)
