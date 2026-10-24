from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_port_a_page_shows_auto_processing_mode(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.get("/workstations/port-a/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "A口入库/复核" in content
    assert "自动处理" in content
    assert "随 Django 网页服务自动启动" in content
    assert 'name="action" value="start"' not in content
    assert 'name="action" value="stop"' not in content


@pytest.mark.django_db
def test_port_b_page_loads(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.get("/workstations/port-b/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "B口出库" in content
    assert "提交状态" in content
    assert "最近提交" in content
