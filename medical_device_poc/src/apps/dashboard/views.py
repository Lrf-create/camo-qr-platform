from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.operations.models import Circulation, OperationRecord
from apps.submissions.models import PortASubmission, PortBSubmission, SubmissionStatus
from apps.workstations.models import WorkstationControl
from apps.dashboard.display_services import get_display_scan_cursor, get_latest_sterile_supply_display


@login_required
def index(request):
    context = {
        "box_status_counts": _box_status_counts(),
        "submission_status_counts": _combined_submission_status_counts(),
        "latest_records": OperationRecord.objects.select_related("box").order_by("-created_at")[:5],
        "latest_port_a": PortASubmission.objects.order_by("-created_at", "-id").first(),
        "latest_port_b": PortBSubmission.objects.order_by("-created_at", "-id").first(),
    }
    return render(request, "dashboard/index.html", context)


@login_required
def system_status(request):
    context = {
        "database_name": connection.settings_dict["NAME"],
        "database_host": connection.settings_dict["HOST"],
        "database_port": connection.settings_dict["PORT"],
        "poll_interval": settings.POLL_INTERVAL_SECONDS,
        "instrument_type_count": InstrumentType.objects.count(),
        "box_count": InstrumentBox.objects.count(),
        "box_inventory_count": BoxInventory.objects.count(),
        "open_circulation_count": Circulation.objects.filter(status=Circulation.Status.OPEN).count(),
        "operation_record_count": OperationRecord.objects.count(),
        "port_a_submission_count": PortASubmission.objects.count(),
        "port_b_submission_count": PortBSubmission.objects.count(),
        "workstations": WorkstationControl.objects.order_by("port"),
        "port_a_ready_count": PortASubmission.objects.filter(status=SubmissionStatus.READY).count(),
        "port_b_ready_count": PortBSubmission.objects.filter(status=SubmissionStatus.READY).count(),
    }
    return render(request, "dashboard/system_status.html", context)


@never_cache
def sterile_supply_display(request):
    return render(request, "display/sterile_supply.html", {"scan_start_id": get_display_scan_cursor()})


@never_cache
def sterile_supply_latest_api(request):
    if request.GET.get("cursor_only") == "1":
        return JsonResponse({"scan_start_id": get_display_scan_cursor()})
    try:
        after_id = int(request.GET.get("after_id", "0"))
        if after_id < 0 or after_id > 9223372036854775807:
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "invalid_scan_cursor"}, status=400)
    return JsonResponse(get_latest_sterile_supply_display(after_id=after_id))


def _box_status_counts():
    counts = {
        row["status"]: row["total"]
        for row in InstrumentBox.objects.values("status").annotate(total=Count("id"))
    }
    return [
        {"status": status, "label": label, "count": counts.get(status, 0)}
        for status, label in InstrumentBox.BoxStatus.choices
    ]


def _combined_submission_status_counts():
    counts = {status: 0 for status, _label in SubmissionStatus.choices}
    for model in [PortASubmission, PortBSubmission]:
        rows = model.objects.values("status").annotate(total=Count("id"))
        for row in rows:
            counts[row["status"]] += row["total"]
    return [
        {"status": status, "label": label, "count": counts[status]}
        for status, label in SubmissionStatus.choices
    ]
