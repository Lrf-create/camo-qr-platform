from __future__ import annotations

from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("records/", views.records, name="records"),
    path("records/<int:record_id>/report/", views.report_detail, name="report_detail"),
]
