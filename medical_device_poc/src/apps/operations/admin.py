from __future__ import annotations

from django.contrib import admin

from .models import Circulation, CirculationItem, OperationRecord, OperationRecordItem

admin.site.register(Circulation)
admin.site.register(CirculationItem)
admin.site.register(OperationRecord)
admin.site.register(OperationRecordItem)
