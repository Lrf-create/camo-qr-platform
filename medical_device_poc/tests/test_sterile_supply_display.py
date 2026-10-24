from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from apps.inventory.models import BoxInventory, InstrumentBox
from apps.submissions.models import PortASubmission, SubmissionStatus
from apps.submissions.services import process_all_ready_once


def create_display_submission(box: InstrumentBox, *, created_at=None) -> PortASubmission:
    submission = PortASubmission.objects.create(
        session_id=uuid.uuid4(),
        qr_token_raw=str(box.qr_token),
        status=SubmissionStatus.READY,
        ready_at=timezone.now(),
    )
    if created_at is not None:
        PortASubmission.objects.filter(pk=submission.pk).update(created_at=created_at)
        submission.refresh_from_db()
    return submission


@pytest.mark.django_db
def test_sterile_supply_api_displays_oldest_ready_port_a_submission(client, seeded_db):
    older = create_display_submission(InstrumentBox.objects.get(box_code="BOX-001"))
    newer = create_display_submission(InstrumentBox.objects.get(box_code="BOX-002"))

    response = client.get("/display/sterile-supply/api/latest/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    payload = response.json()
    older.refresh_from_db()
    newer.refresh_from_db()
    box = InstrumentBox.objects.get(box_code="BOX-001")

    assert payload["has_update"] is True
    assert payload["package_number"] == box.box_code
    assert payload["package_number"] != str(box.qr_token)
    assert payload["package_name"] == box.box_name
    assert len(payload["left_items"]) == 5
    assert len(payload["right_items"]) == 5
    expected_items = [
        {"name": item.instrument_type.display_name, "quantity": item.expected_num}
        for item in BoxInventory.objects.filter(box=box)
        .select_related("instrument_type")
        .order_by("instrument_type__type_code")
    ]
    assert payload["left_items"][:3] == expected_items
    assert payload["left_items"][3:] == [{"name": "", "quantity": ""}, {"name": "", "quantity": ""}]
    assert payload["right_items"] == [{"name": "", "quantity": ""} for _index in range(5)]
    assert older.status == SubmissionStatus.DISPLAYED
    assert older.result_code == ""
    assert older.result_message == ""
    assert older.processed_at is None
    assert newer.status == SubmissionStatus.READY


@pytest.mark.django_db
def test_sterile_supply_api_skips_regular_port_a_submission_with_items(
    client, seeded_db, create_submission
):
    regular = create_submission("A", "BOX-001", {})
    display = create_display_submission(InstrumentBox.objects.get(box_code="BOX-002"))

    response = client.get("/display/sterile-supply/api/latest/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    regular.refresh_from_db()
    display.refresh_from_db()
    assert regular.status == SubmissionStatus.READY
    assert display.status == SubmissionStatus.DISPLAYED


@pytest.mark.django_db
def test_regular_submission_processor_leaves_display_only_submission_ready(seeded_db):
    display = create_display_submission(InstrumentBox.objects.get(box_code="BOX-001"))

    processed = process_all_ready_once(require_running=False)

    display.refresh_from_db()
    assert processed == []
    assert display.status == SubmissionStatus.READY


@pytest.mark.django_db
def test_sterile_supply_api_marks_unknown_qr_as_data_error_without_update(client, seeded_db):
    submission = PortASubmission.objects.create(
        session_id=uuid.uuid4(),
        qr_token_raw=str(uuid.uuid4()),
        status=SubmissionStatus.READY,
        ready_at=timezone.now(),
    )

    response = client.get("/display/sterile-supply/api/latest/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    assert response.json() == {"has_update": False}
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DATA_ERROR
    assert submission.result_code == "UNKNOWN_QR"
    assert submission.result_message == "二维码错误：未找到对应器械框"


@pytest.mark.django_db
def test_sterile_supply_page_is_public(client):
    response = client.get("/display/sterile-supply/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "消毒供应室智能检测岛台" in content
    assert "sidebar" not in content


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", ["\n", "\r\n", " "])
def test_display_matches_uuid_with_scanner_trailing_whitespace(client, seeded_db, suffix):
    box = InstrumentBox.objects.get(box_code="BOX-001")
    submission = create_display_submission(box)
    submission.qr_token_raw = " " + str(box.qr_token) + suffix
    submission.save(update_fields=["qr_token_raw"])
    response = client.get("/display/sterile-supply/api/latest/", HTTP_HOST="127.0.0.1")
    assert response.json()["package_number"] == "BOX-001"
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.DISPLAYED
    assert submission.qr_token_raw.endswith(suffix)


@pytest.mark.django_db
def test_repeated_reads_and_second_browser_keep_latest_scan_visible(client, seeded_db):
    from django.test import Client

    first = create_display_submission(InstrumentBox.objects.get(box_code="BOX-001"))
    url = "/display/sterile-supply/api/latest/"
    payload = client.get(url, HTTP_HOST="127.0.0.1").json()
    assert payload["package_number"] == "BOX-001"
    assert client.get(url, HTTP_HOST="127.0.0.1").json() == payload
    other_browser = Client()
    assert other_browser.get(url, HTTP_HOST="127.0.0.1").json() == payload
    second = create_display_submission(InstrumentBox.objects.get(box_code="BOX-002"))
    assert other_browser.get(url, HTTP_HOST="127.0.0.1").json()["package_number"] == "BOX-002"
    response = client.get(url, HTTP_HOST="127.0.0.1")
    assert response.json()["package_number"] == "BOX-002"
    assert "no-store" in response.headers["Cache-Control"]
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == second.status == SubmissionStatus.DISPLAYED


@pytest.mark.django_db
def test_empty_display_has_no_update(client):
    response = client.get("/display/sterile-supply/api/latest/", HTTP_HOST="127.0.0.1")
    assert response.json() == {"has_update": False}


@pytest.mark.django_db
def test_new_display_session_ignores_previous_ready_and_displayed_scans(client, seeded_db):
    import re

    old = create_display_submission(InstrumentBox.objects.get(box_code="BOX-001"))
    page = client.get("/display/sterile-supply/", HTTP_HOST="127.0.0.1")
    cursor = int(re.search(r'data-scan-start-id="(\d+)"', page.content.decode()).group(1))
    assert cursor == old.id
    assert '<dd id="sterile-package-number"></dd>' in page.content.decode()
    api = f"/display/sterile-supply/api/latest/?after_id={cursor}"
    assert client.get(api, HTTP_HOST="127.0.0.1").json() == {"has_update": False}
    old.refresh_from_db()
    assert old.status == SubmissionStatus.READY
    new = create_display_submission(InstrumentBox.objects.get(box_code="BOX-002"))
    assert client.get(api, HTTP_HOST="127.0.0.1").json()["package_number"] == "BOX-002"
    assert client.get(api, HTTP_HOST="127.0.0.1").json()["package_number"] == "BOX-002"
    reopened = client.get("/display/sterile-supply/", HTTP_HOST="127.0.0.1")
    reopened_cursor = int(re.search(r'data-scan-start-id="(\d+)"', reopened.content.decode()).group(1))
    assert reopened_cursor == new.id
    assert client.get(f"/display/sterile-supply/api/latest/?after_id={reopened_cursor}", HTTP_HOST="127.0.0.1").json() == {"has_update": False}
    new.refresh_from_db()
    assert new.status == SubmissionStatus.DISPLAYED


@pytest.mark.django_db
def test_cursor_query_does_not_consume_scans_and_bad_cursor_is_rejected(client, seeded_db):
    row = create_display_submission(InstrumentBox.objects.get(box_code="BOX-001"))
    response = client.get("/display/sterile-supply/api/latest/?cursor_only=1", HTTP_HOST="127.0.0.1")
    assert response.json() == {"scan_start_id": row.id}
    row.refresh_from_db()
    assert row.status == SubmissionStatus.READY
    for invalid in ["-1", "hello", "9223372036854775808"]:
        assert client.get(f"/display/sterile-supply/api/latest/?after_id={invalid}", HTTP_HOST="127.0.0.1").status_code == 400
