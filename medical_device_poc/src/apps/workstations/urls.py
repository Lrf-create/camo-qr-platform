from __future__ import annotations

from django.urls import path

from . import views

app_name = "workstations"

urlpatterns = [
    path("port-a/", views.port_a, name="port_a"),
    path("port-b/", views.port_b, name="port_b"),
]
