from __future__ import annotations

import pytest

from apps.submissions.services import process_all_ready_once

BOX_001_NUMS = {"FORCEPS": 2, "SCALPEL": 1, "SCISSORS": 3}


@pytest.mark.django_db
def test_dashboard_index_shows_summary_and_recent_activity(client, django_user_model, seeded_db, create_submission):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    create_submission("B", "BOX-001", BOX_001_NUMS)
    assert len(process_all_ready_once(require_running=False)) == 1

    response = client.get("/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "实时看板" in content
    assert "器械框状态" in content
    assert "提交状态" in content
    assert "最近操作记录" in content
    assert "OUTBOUND_SUCCESS" in content


@pytest.mark.django_db
def test_system_status_page_shows_database_and_counts(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.get("/system-status/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "系统状态" in content
    assert "数据库" in content
    assert "随 Web 服务自动处理" in content
    assert "器械种类" in content
    assert "器械框" in content
    assert "A口待处理" in content
    assert "B口待处理" in content
