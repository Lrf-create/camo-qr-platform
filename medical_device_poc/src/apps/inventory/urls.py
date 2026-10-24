from __future__ import annotations

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("instrument-types/", views.instrument_types, name="instrument_types"),
    path("instrument-types/new/", views.create_instrument_type, name="create_instrument_type"),
    path("instrument-types/<int:instrument_type_id>/edit/", views.edit_instrument_type, name="edit_instrument_type"),
    path(
        "instrument-types/<int:instrument_type_id>/delete/",
        views.delete_instrument_type_view,
        name="delete_instrument_type",
    ),
    path("boxes/", views.boxes, name="boxes"),
    path("boxes/new/", views.create_box, name="create_box"),
    path("boxes/<int:box_id>/edit/", views.edit_box, name="edit_box"),
    path("boxes/<int:box_id>/delete/", views.delete_box_view, name="delete_box"),
    path("boxes/<int:box_id>/inventory/", views.edit_box_inventory, name="edit_box_inventory"),
    path("status-query/", views.status_query, name="status_query"),
]
