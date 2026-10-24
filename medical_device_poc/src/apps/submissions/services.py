from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Type

from django.db import transaction
from django.db.models import Exists, Model, OuterRef, QuerySet
from django.utils import timezone

from apps.inventory.models import InstrumentBox, InstrumentType
from apps.operations.services import QuantityLine, QuantityMap, process_inbound_or_review, process_outbound
from apps.submissions.models import (
    PortASubmission,
    PortASubmissionItem,
    PortBSubmission,
    PortBSubmissionItem,
    SubmissionStatus,
)
from apps.workstations.models import WorkstationControl

Port = Literal["A", "B"]


@dataclass(frozen=True)
class ProcessedSubmission:
    port: Port
    submission_id: int
    session_id: str
    status: str
    result_code: str
    result_message: str


@dataclass(frozen=True)
class PortModels:
    submission_model: Type[PortASubmission] | Type[PortBSubmission]
    item_model: Type[PortASubmissionItem] | Type[PortBSubmissionItem]


PORT_MODELS: dict[Port, PortModels] = {
    "A": PortModels(PortASubmission, PortASubmissionItem),
    "B": PortModels(PortBSubmission, PortBSubmissionItem),
}


def process_next_ready_submission(port: Port, *, require_running: bool = True) -> ProcessedSubmission | None:
    models = PORT_MODELS[port]
    with transaction.atomic():
        control = WorkstationControl.objects.select_for_update().get(port=port)
        if require_running and not control.is_running:
            return None

        submission = _next_ready_submission(
            models.submission_model,
            models.item_model,
            require_items=port == "A",
        )
        if submission is None:
            return None

        submission.status = SubmissionStatus.PROCESSING
        submission.save(update_fields=["status"])

        result_status, result_code, result_message = _process_locked_submission(port, submission)
        submission.status = result_status
        submission.result_code = result_code
        submission.result_message = result_message
        submission.processed_at = timezone.now()
        submission.save(update_fields=["status", "result_code", "result_message", "processed_at"])

        return ProcessedSubmission(
            port=port,
            submission_id=submission.id,
            session_id=str(submission.session_id),
            status=result_status,
            result_code=result_code,
            result_message=result_message,
        )


def process_all_ready_once(*, require_running: bool = True) -> list[ProcessedSubmission]:
    processed = []
    while True:
        made_progress = False
        for port in ["A", "B"]:
            result = process_next_ready_submission(port, require_running=require_running)
            if result is not None:
                processed.append(result)
                made_progress = True
        if not made_progress:
            break
    return processed


def _next_ready_submission(
    submission_model: Type[Model],
    item_model: Type[Model],
    *,
    require_items: bool,
) -> Model | None:
    queryset: QuerySet = submission_model.objects.select_for_update(skip_locked=True)
    queryset = queryset.filter(status=SubmissionStatus.READY)
    if require_items:
        has_items = Exists(item_model.objects.filter(submission=OuterRef("pk")))
        queryset = queryset.annotate(has_items=has_items).filter(has_items=True)
    return queryset.order_by("created_at", "id").first()


def _process_locked_submission(port: Port, submission: PortASubmission | PortBSubmission) -> tuple[str, str, str]:
    try:
        box = InstrumentBox.objects.select_for_update().get(qr_token=submission.qr_token_raw)
    except (InstrumentBox.DoesNotExist, ValueError):
        return SubmissionStatus.DATA_ERROR, "UNKNOWN_QR", "二维码错误：未找到对应器械框"

    submitted, error_code, error_message = _build_submitted_quantities(submission)
    if submitted is None:
        return SubmissionStatus.DATA_ERROR, error_code, error_message

    if port == "B":
        result = process_outbound(box, submitted)
    else:
        result = process_inbound_or_review(box, submitted)

    status = (
        SubmissionStatus.SUCCESS
        if result.result == "SUCCESS"
        else SubmissionStatus.BUSINESS_FAILED
    )
    return status, result.code, result.message


def _build_submitted_quantities(
    submission: PortASubmission | PortBSubmission,
) -> tuple[QuantityMap | None, str, str]:
    instruments = {row.type_code: row for row in InstrumentType.objects.all()}
    expected_codes = set(instruments)
    rows = list(submission.items.all())

    if not rows:
        return None, "MISSING_ITEMS", "提交明细为空"

    submitted: QuantityMap = {}
    duplicate_codes = []
    unknown_codes = []

    for row in rows:
        type_code = row.type.upper().strip()
        if type_code in submitted:
            duplicate_codes.append(type_code)
            continue
        instrument = instruments.get(type_code)
        if instrument is None:
            unknown_codes.append(type_code)
            continue
        submitted[type_code] = QuantityLine(instrument_type=instrument, num=row.num)

    if duplicate_codes:
        return None, "DUPLICATE_TYPE", f"提交明细存在重复 TYPE：{', '.join(sorted(set(duplicate_codes)))}"

    if unknown_codes:
        return None, "UNKNOWN_TYPE", f"提交明细存在未知 TYPE：{', '.join(sorted(set(unknown_codes)))}"

    submitted_codes = set(submitted)
    missing_codes = expected_codes - submitted_codes
    extra_codes = submitted_codes - expected_codes
    if missing_codes:
        return None, "MISSING_TYPE", f"提交明细缺少 TYPE：{', '.join(sorted(missing_codes))}"
    if extra_codes:
        return None, "UNKNOWN_TYPE", f"提交明细存在未知 TYPE：{', '.join(sorted(extra_codes))}"

    return submitted, "", ""
