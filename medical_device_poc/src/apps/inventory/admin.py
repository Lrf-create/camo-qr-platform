from __future__ import annotations

from django.contrib import admin

from .models import BoxInventory, InstrumentBox, InstrumentType

admin.site.register(InstrumentType)
admin.site.register(InstrumentBox)
admin.site.register(BoxInventory)
