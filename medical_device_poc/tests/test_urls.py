from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_authenticated_core_pages_return_200(client, django_user_model, seeded_db):
    user = django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    paths = [
        "/",
        "/inventory/instrument-types/",
        "/inventory/boxes/",
        "/inventory/status-query/",
        "/operations/records/",
        "/workstations/port-a/",
        "/workstations/port-b/",
        "/system-status/",
    ]
    for path in paths:
        assert client.get(path, HTTP_HOST="127.0.0.1").status_code == 200
