from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.db.models import Exists, Max, OuterRef
from django.utils import timezone

from apps.inventory.models import BoxInventory, InstrumentBox
from apps.submissions.models import PortASubmission, PortASubmissionItem, SubmissionStatus

UNKNOWN_QR_MESSAGE = "二维码错误：未找到对应器械框"


def get_display_scan_cursor() -> int:
    return PortASubmission.objects.aggregate(latest=Max("id"))["latest"] or 0


def get_latest_sterile_supply_display(*, after_id: int = 0) -> dict[str, Any]:
    with transaction.atomic():
        submission = (
            PortASubmission.objects.select_for_update(skip_locked=True)
            .filter(status=SubmissionStatus.READY, id__gt=after_id)
            .annotate(
                has_items=Exists(
                    PortASubmissionItem.objects.filter(submission=OuterRef("pk"))
                )
            )
            .filter(has_items=False)
            .order_by("created_at", "id")
            .first()
        )
        if submission is None:
            # A refresh or a second display must see the last accepted scan too.
            # Reading the current display does not consume or alter its record.
            current = (
                PortASubmission.objects.filter(
                    status=SubmissionStatus.DISPLAYED, items__isnull=True, id__gt=after_id
                )
                .order_by("-created_at", "-id")
                .first()
            )
            box = _find_box(current.qr_token_raw) if current else None
            return _build_display_payload(box) if box else {"has_update": False}

        box = _find_box(submission.qr_token_raw)
        if box is None:
            submission.status = SubmissionStatus.DATA_ERROR
            submission.result_code = "UNKNOWN_QR"
            submission.result_message = UNKNOWN_QR_MESSAGE
            submission.processed_at = timezone.now()
            submission.save(update_fields=["status", "result_code", "result_message", "processed_at"])
            return {"has_update": False}

        payload = _build_display_payload(box)
        submission.status = SubmissionStatus.DISPLAYED
        submission.save(update_fields=["status"])
        return payload


def _find_box(qr_token_raw: str) -> InstrumentBox | None:
    try:
        qr_token = uuid.UUID(qr_token_raw.strip())
    except (TypeError, ValueError):
        return None
    return InstrumentBox.objects.filter(qr_token=qr_token).first()


def _build_display_payload(box: InstrumentBox) -> dict[str, Any]:
    inventory_items = list(
        BoxInventory.objects.filter(box=box)
        .select_related("instrument_type")
        .order_by("instrument_type__type_code")[:10]
    )
    rows = [
        {"name": item.instrument_type.display_name, "quantity": item.expected_num}
        for item in inventory_items
    ]
    while len(rows) < 10:
        rows.append({"name": "", "quantity": ""})

    return {
        "has_update": True,
        "package_number": box.box_code,
        "package_name": box.box_name,
        "left_items": rows[:5],
        "right_items": rows[5:10],
    }
