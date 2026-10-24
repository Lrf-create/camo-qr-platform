from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.operations.models import OperationRecord


@login_required
def records(request):
    result_filter = request.GET.get("result", "")
    operation_filter = request.GET.get("operation_type", "")
    records_qs = OperationRecord.objects.select_related("box", "circulation").order_by("-created_at")

    if result_filter:
        records_qs = records_qs.filter(result=result_filter)
    if operation_filter:
        records_qs = records_qs.filter(operation_type=operation_filter)

    context = {
        "records": records_qs[:100],
        "result_filter": result_filter,
        "operation_filter": operation_filter,
        "result_choices": OperationRecord.Result.choices,
        "operation_choices": OperationRecord.OperationType.choices,
    }
    return render(request, "operations/records.html", context)


@login_required
def report_detail(request, record_id: int):
    record = get_object_or_404(
        OperationRecord.objects.select_related("box", "circulation").prefetch_related("items"),
        id=record_id,
    )
    context = {
        "record": record,
        "items": record.items.all(),
    }
    return render(request, "operations/report_detail.html", context)
