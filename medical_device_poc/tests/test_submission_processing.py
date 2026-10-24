from __future__ import annotations

import uuid

from django.core.management import call_command
from django.utils import timezone

from apps.inventory.models import InstrumentBox
from apps.operations.models import Circulation, OperationRecord
from apps.submissions.models import PortASubmission, PortBSubmission, SubmissionStatus
from apps.submissions.services import process_all_ready_once
from apps.workstations.services import start_workstation

BOX_001_NUMS = {"FORCEPS": 2, "SCALPEL": 1, "SCISSORS": 3}
BOX_002_NUMS = {"FORCEPS": 1, "SCALPEL": 2, "SCISSORS": 1}


def test_auto_mode_processes_ready_submission_without_manual_start(seeded_db, create_submission):
    submission = create_submission("B", "BOX-001", BOX_001_NUMS)

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.SUCCESS
    assert submission.result_code == "OUTBOUND_SUCCESS"


def test_manual_gated_mode_still_requires_running_port(seeded_db, create_submission):
    submission = create_submission("B", "BOX-001", BOX_001_NUMS)

    assert process_all_ready_once() == []
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.READY

    start_workstation("B")
    assert len(process_all_ready_once()) == 1


def test_successful_outbound_then_inbound_closes_circulation(seeded_db, create_submission):
    outbound = create_submission("B", "BOX-001", BOX_001_NUMS)

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    outbound.refresh_from_db()
    box = InstrumentBox.objects.get(box_code="BOX-001")
    assert outbound.status == SubmissionStatus.SUCCESS
    assert box.status == InstrumentBox.BoxStatus.OUTBOUND
    assert box.flow_count == 0
    assert Circulation.objects.filter(box=box, status=Circulation.Status.OPEN).count() == 1

    inbound = create_submission("A", "BOX-001", BOX_001_NUMS)

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    inbound.refresh_from_db()
    box.refresh_from_db()
    assert inbound.status == SubmissionStatus.SUCCESS
    assert inbound.result_code == "INBOUND_SUCCESS"
    assert box.status == InstrumentBox.BoxStatus.IN_STOCK
    assert box.flow_count == 1
    assert Circulation.objects.filter(box=box, status=Circulation.Status.OPEN).count() == 0
    assert list(OperationRecord.objects.order_by("created_at").values_list("operation_type", "result")) == [
        (OperationRecord.OperationType.OUTBOUND, OperationRecord.Result.SUCCESS),
        (OperationRecord.OperationType.INBOUND, OperationRecord.Result.SUCCESS),
    ]


def test_unknown_qr_is_data_error_without_operation_record(seeded_db, create_submission):
    submission = create_submission(
        "B",
        None,
        {"FORCEPS": 0, "SCALPEL": 0, "SCISSORS": 0},
        qr_token="00000000-0000-0000-0000-000000000000",
    )

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DATA_ERROR
    assert submission.result_code == "UNKNOWN_QR"
    assert OperationRecord.objects.count() == 0


def test_outbound_quantity_mismatch_is_business_failure_with_record(seeded_db, create_submission):
    submission = create_submission("B", "BOX-002", {"FORCEPS": 99, "SCALPEL": 2, "SCISSORS": 1})

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    box = InstrumentBox.objects.get(box_code="BOX-002")
    record = OperationRecord.objects.get()
    item = record.items.get(type_code_snapshot="FORCEPS")
    assert submission.status == SubmissionStatus.BUSINESS_FAILED
    assert submission.result_code == "QUANTITY_MISMATCH"
    assert box.status == InstrumentBox.BoxStatus.IN_STOCK
    assert record.result == OperationRecord.Result.BUSINESS_FAILED
    assert item.submitted_num == 99
    assert item.expected_num == 1
    assert item.diff_num == 98


def test_inbound_mismatch_then_review_success(seeded_db, create_submission):
    create_submission("B", "BOX-002", BOX_002_NUMS)
    assert len(process_all_ready_once(require_running=False)) == 1

    mismatch = create_submission("A", "BOX-002", {"FORCEPS": 0, "SCALPEL": 2, "SCISSORS": 1})
    assert len(process_all_ready_once(require_running=False)) == 1

    box = InstrumentBox.objects.get(box_code="BOX-002")
    mismatch.refresh_from_db()
    assert mismatch.status == SubmissionStatus.BUSINESS_FAILED
    assert box.status == InstrumentBox.BoxStatus.INBOUND
    assert Circulation.objects.filter(box=box, status=Circulation.Status.OPEN).count() == 1

    review = create_submission("A", "BOX-002", BOX_002_NUMS)
    assert len(process_all_ready_once(require_running=False)) == 1

    box.refresh_from_db()
    review.refresh_from_db()
    assert review.status == SubmissionStatus.SUCCESS
    assert review.result_code == "REVIEW_SUCCESS"
    assert box.status == InstrumentBox.BoxStatus.IN_STOCK
    assert box.flow_count == 1
    assert Circulation.objects.filter(box=box, status=Circulation.Status.OPEN).count() == 0


def test_missing_type_is_data_error_without_operation_record(seeded_db, create_submission):
    submission = create_submission("B", "BOX-001", BOX_001_NUMS)
    submission.items.filter(type="SCALPEL").delete()

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DATA_ERROR
    assert submission.result_code == "MISSING_TYPE"
    assert OperationRecord.objects.count() == 0


def test_unknown_type_is_data_error_without_operation_record(seeded_db, create_submission):
    submission = create_submission("B", "BOX-001", BOX_001_NUMS)
    item = submission.items.get(type="SCALPEL")
    item.type = "UNKNOWN_TYPE"
    item.save(update_fields=["type"])

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DATA_ERROR
    assert submission.result_code == "UNKNOWN_TYPE"
    assert OperationRecord.objects.count() == 0


def test_port_b_empty_submission_is_processed_as_data_error(seeded_db):
    submission = PortBSubmission.objects.create(
        session_id=uuid.uuid4(),
        qr_token_raw=str(InstrumentBox.objects.get(box_code="BOX-001").qr_token),
        status=SubmissionStatus.READY,
        ready_at=timezone.now(),
    )

    processed = process_all_ready_once(require_running=False)

    assert len(processed) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DATA_ERROR
    assert submission.result_code == "MISSING_ITEMS"


def test_process_command_once_handles_ready_submission(seeded_db, create_submission):
    submission = create_submission("B", "BOX-001", BOX_001_NUMS)

    call_command("process_submissions", "--once", verbosity=0)

    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.SUCCESS
    assert PortBSubmission.objects.filter(status=SubmissionStatus.READY).count() == 0
    assert PortASubmission.objects.filter(status=SubmissionStatus.READY).count() == 0
