from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("operations/", include("apps.operations.urls")),
    path("submissions/", include("apps.submissions.urls")),
    path("workstations/", include("apps.workstations.urls")),
]
