from __future__ import annotations

import pytest

from apps.operations.models import OperationRecord
from apps.submissions.models import SubmissionStatus
from apps.submissions.services import process_all_ready_once


@pytest.mark.django_db
def test_operation_records_list_and_report_detail(client, django_user_model, seeded_db, create_submission):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    submission = create_submission("B", "BOX-002", {"FORCEPS": 99, "SCALPEL": 2, "SCISSORS": 1})
    assert len(process_all_ready_once(require_running=False)) == 1
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.BUSINESS_FAILED

    record = OperationRecord.objects.get()

    response = client.get("/operations/records/", HTTP_HOST="127.0.0.1")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "操作记录" in content
    assert "业务失败" in content
    assert "BOX-002" in content
    assert "查看明细" in content

    response = client.get(f"/operations/records/{record.id}/report/", HTTP_HOST="127.0.0.1")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "差异报告" in content
    assert "FORCEPS" in content
    assert "99" in content
    assert "1" in content
    assert "98" in content


@pytest.mark.django_db
def test_operation_records_filter(client, django_user_model, seeded_db, create_submission):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    create_submission("B", "BOX-002", {"FORCEPS": 99, "SCALPEL": 2, "SCISSORS": 1})
    assert len(process_all_ready_once(require_running=False)) == 1

    response = client.get(
        "/operations/records/?result=BUSINESS_FAILED&operation_type=OUTBOUND",
        HTTP_HOST="127.0.0.1",
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "业务失败" in content
    assert "出库" in content
