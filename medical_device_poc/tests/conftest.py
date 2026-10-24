from __future__ import annotations

import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.inventory.models import InstrumentBox, InstrumentType
from apps.submissions.models import (
    PortASubmission,
    PortASubmissionItem,
    PortBSubmission,
    PortBSubmissionItem,
    SubmissionStatus,
)


@pytest.fixture
def seeded_db(db):
    call_command("seed_demo_data", verbosity=0)


@pytest.fixture
def create_submission(seeded_db):
    def _create_submission(port: str, box_code: str | None, nums: dict[str, int], qr_token: str | None = None):
        if qr_token is None:
            if box_code is None:
                raise ValueError("box_code is required when qr_token is not provided")
            box = InstrumentBox.objects.get(box_code=box_code)
            qr_token = str(box.qr_token)

        if port == "A":
            submission = PortASubmission.objects.create(
                session_id=uuid.uuid4(),
                qr_token_raw=qr_token,
                status=SubmissionStatus.READY,
                ready_at=timezone.now(),
            )
            item_model = PortASubmissionItem
        elif port == "B":
            submission = PortBSubmission.objects.create(
                session_id=uuid.uuid4(),
                qr_token_raw=qr_token,
                status=SubmissionStatus.READY,
                ready_at=timezone.now(),
            )
            item_model = PortBSubmissionItem
        else:
            raise ValueError(f"Unsupported port: {port}")

        for instrument_type in InstrumentType.objects.order_by("type_code"):
            item_model.objects.create(
                submission=submission,
                type=instrument_type.type_code,
                num=nums.get(instrument_type.type_code, 0),
            )
        return submission

    return _create_submission
