from __future__ import annotations

import uuid

import pytest

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType


@pytest.mark.django_db
def test_instrument_types_page_lists_type_codes(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.get("/inventory/instrument-types/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "器械种类" in content
    assert "FORCEPS" in content
    assert "SCALPEL" in content
    assert "SCISSORS" in content
    assert "配置总量" in content
    assert "新增器械种类" in content
    assert "编辑" in content
    assert "删除" in content


@pytest.mark.django_db
def test_boxes_page_lists_boxes_and_inventory(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.get("/inventory/boxes/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "BOX-001" in content
    assert "二维码字符串" in content
    assert "FORCEPS：2" in content
    assert "SCALPEL：1" in content
    assert "SCISSORS：3" in content
    assert "编辑配置" in content
    assert "新增器械框" in content
    assert "编辑资料" in content
    assert "删除" in content


@pytest.mark.django_db
def test_status_query_page_summarizes_by_box_status(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")
    box.status = InstrumentBox.BoxStatus.OUTBOUND
    box.save(update_fields=["status", "updated_at"])

    response = client.get("/inventory/status-query/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "器械状态查询" in content
    assert "FORCEPS" in content
    assert "出库数量" in content
    assert "在库数量" in content


@pytest.mark.django_db
def test_edit_box_inventory_page_loads(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")

    response = client.get(f"/inventory/boxes/{box.id}/inventory/", HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "编辑框内配置" in content
    assert "BOX-001" in content
    assert "FORCEPS" in content
    assert "保存配置" in content


@pytest.mark.django_db
def test_edit_box_inventory_updates_quantities(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")
    items = list(box.inventory_items.order_by("instrument_type__type_code"))
    payload = {f"num_{item.instrument_type_id}": str(index + 4) for index, item in enumerate(items)}

    response = client.post(
        f"/inventory/boxes/{box.id}/inventory/",
        payload,
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    nums = list(
        BoxInventory.objects.filter(box=box)
        .order_by("instrument_type__type_code")
        .values_list("expected_num", flat=True)
    )
    assert nums == [4, 5, 6]
    assert "器械框配置已保存" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_edit_box_inventory_rejects_negative_quantity(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")
    items = list(box.inventory_items.order_by("instrument_type__type_code"))
    original_nums = list(
        BoxInventory.objects.filter(box=box)
        .order_by("instrument_type__type_code")
        .values_list("expected_num", flat=True)
    )
    payload = {f"num_{item.instrument_type_id}": "1" for item in items}
    payload[f"num_{items[0].instrument_type_id}"] = "-1"

    response = client.post(
        f"/inventory/boxes/{box.id}/inventory/",
        payload,
        HTTP_HOST="127.0.0.1",
    )

    assert response.status_code == 200
    nums = list(
        BoxInventory.objects.filter(box=box)
        .order_by("instrument_type__type_code")
        .values_list("expected_num", flat=True)
    )
    assert nums == original_nums
    assert "数量不能小于 0" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_edit_box_inventory_rejects_non_in_stock_box(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")
    box.status = InstrumentBox.BoxStatus.OUTBOUND
    box.save(update_fields=["status", "updated_at"])
    original_nums = list(
        BoxInventory.objects.filter(box=box)
        .order_by("instrument_type__type_code")
        .values_list("expected_num", flat=True)
    )
    payload = {
        f"num_{item.instrument_type_id}": "9"
        for item in box.inventory_items.order_by("instrument_type__type_code")
    }

    response = client.post(
        f"/inventory/boxes/{box.id}/inventory/",
        payload,
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    nums = list(
        BoxInventory.objects.filter(box=box)
        .order_by("instrument_type__type_code")
        .values_list("expected_num", flat=True)
    )
    assert nums == original_nums
    content = response.content.decode("utf-8")
    assert "配置不可修改" in content
    assert "只有在库状态的器械框可以修改配置" in content


@pytest.mark.django_db
def test_create_instrument_type_adds_default_inventory_rows(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.post(
        "/inventory/instrument-types/new/",
        {"type_code": "clamp", "display_name": "止血夹"},
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    instrument_type = InstrumentType.objects.get(type_code="CLAMP")
    assert instrument_type.display_name == "止血夹"
    assert BoxInventory.objects.filter(instrument_type=instrument_type).count() == InstrumentBox.objects.count()
    assert set(
        BoxInventory.objects.filter(instrument_type=instrument_type).values_list("expected_num", flat=True)
    ) == {0}
    content = response.content.decode("utf-8")
    assert "器械种类已创建" in content
    assert "CLAMP" in content


@pytest.mark.django_db
def test_edit_instrument_type_updates_code_and_name(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    instrument_type = InstrumentType.objects.get(type_code="FORCEPS")

    response = client.post(
        f"/inventory/instrument-types/{instrument_type.id}/edit/",
        {"type_code": "forceps_new", "display_name": "新镊子"},
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    instrument_type.refresh_from_db()
    assert instrument_type.type_code == "FORCEPS_NEW"
    assert instrument_type.display_name == "新镊子"
    assert "器械种类已保存" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_delete_unused_instrument_type_removes_default_inventory_rows(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    instrument_type = InstrumentType.objects.create(type_code="DRILL", display_name="钻头")
    for box in InstrumentBox.objects.all():
        BoxInventory.objects.create(box=box, instrument_type=instrument_type, expected_num=0)

    response = client.post(
        f"/inventory/instrument-types/{instrument_type.id}/delete/",
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    assert not InstrumentType.objects.filter(type_code="DRILL").exists()
    assert "器械种类已删除" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_create_box_generates_qr_and_default_inventory_rows(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")

    response = client.post(
        "/inventory/boxes/new/",
        {"box_code": "box-004", "box_name": "第四框"},
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    box = InstrumentBox.objects.get(box_code="BOX-004")
    assert box.box_name == "第四框"
    assert box.status == InstrumentBox.BoxStatus.IN_STOCK
    assert box.flow_count == 0
    assert box.qr_token
    assert BoxInventory.objects.filter(box=box).count() == InstrumentType.objects.count()
    assert set(BoxInventory.objects.filter(box=box).values_list("expected_num", flat=True)) == {0}
    content = response.content.decode("utf-8")
    assert "器械框已创建" in content
    assert "BOX-004" in content


@pytest.mark.django_db
def test_edit_box_updates_basic_fields_without_changing_qr(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.get(box_code="BOX-001")
    original_qr_token = box.qr_token

    response = client.post(
        f"/inventory/boxes/{box.id}/edit/",
        {"box_code": "box-001-new", "box_name": "一号框更新"},
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    box.refresh_from_db()
    assert box.box_code == "BOX-001-NEW"
    assert box.box_name == "一号框更新"
    assert box.qr_token == original_qr_token
    assert "器械框资料已保存" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_delete_unused_box_removes_default_inventory_rows(client, django_user_model, seeded_db):
    django_user_model.objects.create_user(username="tester", password="123456")
    assert client.login(username="tester", password="123456")
    box = InstrumentBox.objects.create(box_code="BOX-DELETE", box_name="待删除框", qr_token=uuid.uuid4())
    for instrument_type in InstrumentType.objects.all():
        BoxInventory.objects.create(box=box, instrument_type=instrument_type, expected_num=0)

    response = client.post(
        f"/inventory/boxes/{box.id}/delete/",
        HTTP_HOST="127.0.0.1",
        follow=True,
    )

    assert response.status_code == 200
    assert not InstrumentBox.objects.filter(box_code="BOX-DELETE").exists()
    assert "器械框已删除" in response.content.decode("utf-8")
