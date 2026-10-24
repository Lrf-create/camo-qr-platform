from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from apps.submissions.models import PortASubmission, PortBSubmission, SubmissionStatus
from apps.workstations.models import WorkstationControl

PORT_CONFIG = {
    "A": {
        "title": "A口入库/复核",
        "subtitle": "Django 网页服务启动后，A 口提交会自动处理。",
        "panel_title": "A口自动处理",
        "template": "workstations/port_a.html",
        "submission_model": PortASubmission,
    },
    "B": {
        "title": "B口出库",
        "subtitle": "Django 网页服务启动后，B 口提交会自动处理。",
        "panel_title": "B口自动处理",
        "template": "workstations/port_b.html",
        "submission_model": PortBSubmission,
    },
}


@login_required
def port_a(request):
    return _port_view(request, "A")


@login_required
def port_b(request):
    return _port_view(request, "B")


def _port_view(request, port: str):
    config = PORT_CONFIG[port]
    submission_model = config["submission_model"]
    control, _created = WorkstationControl.objects.get_or_create(port=port)
    status_counts = _submission_status_counts(submission_model)
    latest_submission = submission_model.objects.order_by("-created_at", "-id").first()

    context = {
        **config,
        "port": port,
        "control": control,
        "status_counts": status_counts,
        "latest_submission": latest_submission,
    }
    return render(request, config["template"], context)


def _submission_status_counts(submission_model):
    counts = {status: 0 for status, _label in SubmissionStatus.choices}
    rows = submission_model.objects.values("status").annotate(total=Count("id"))
    for row in rows:
        counts[row["status"]] = row["total"]
    return [
        {"status": status, "label": label, "count": counts[status]}
        for status, label in SubmissionStatus.choices
    ]
