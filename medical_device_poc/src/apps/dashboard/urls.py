from __future__ import annotations

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("display/sterile-supply/", views.sterile_supply_display, name="sterile_supply_display"),
    path("display/sterile-supply/api/latest/", views.sterile_supply_latest_api, name="sterile_supply_latest_api"),
    path("system-status/", views.system_status, name="system_status"),
]
