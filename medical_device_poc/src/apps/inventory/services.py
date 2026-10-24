from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType


def can_edit_box_inventory(box: InstrumentBox) -> bool:
    return box.status == InstrumentBox.BoxStatus.IN_STOCK


@transaction.atomic
def create_instrument_type_with_default_inventory(instrument_type: InstrumentType) -> InstrumentType:
    instrument_type.save()
    for box in InstrumentBox.objects.all():
        BoxInventory.objects.get_or_create(
            box=box,
            instrument_type=instrument_type,
            defaults={"expected_num": 0},
        )
    return instrument_type


@transaction.atomic
def create_box_with_default_inventory(box: InstrumentBox) -> InstrumentBox:
    box.status = InstrumentBox.BoxStatus.IN_STOCK
    box.flow_count = 0
    box.save()
    for instrument_type in InstrumentType.objects.all():
        BoxInventory.objects.get_or_create(
            box=box,
            instrument_type=instrument_type,
            defaults={"expected_num": 0},
        )
    return box


@transaction.atomic
def delete_instrument_type(instrument_type: InstrumentType) -> tuple[bool, str]:
    try:
        BoxInventory.objects.filter(instrument_type=instrument_type).delete()
        instrument_type.delete()
    except (ProtectedError, IntegrityError):
        return False, "该器械种类已被操作记录或流转记录引用，不能删除。"
    return True, "器械种类已删除。"


@transaction.atomic
def delete_box(box: InstrumentBox) -> tuple[bool, str]:
    try:
        BoxInventory.objects.filter(box=box).delete()
        box.delete()
    except (ProtectedError, IntegrityError):
        return False, "该器械框已被操作记录或流转记录引用，不能删除。"
    return True, "器械框已删除。"


def parse_inventory_quantities(post_data, instrument_types: list[InstrumentType]) -> tuple[dict[int, int], list[str]]:
    quantities: dict[int, int] = {}
    errors: list[str] = []
    for instrument_type in instrument_types:
        raw_value = post_data.get(f"num_{instrument_type.id}", "").strip()
        try:
            value = int(raw_value)
        except ValueError:
            errors.append(f"{instrument_type.type_code} 的数量必须是非负整数。")
            continue
        if value < 0:
            errors.append(f"{instrument_type.type_code} 的数量不能小于 0。")
            continue
        quantities[instrument_type.id] = value
    return quantities, errors


@transaction.atomic
def save_box_inventory(box: InstrumentBox, instrument_types: list[InstrumentType], quantities: dict[int, int]) -> None:
    for instrument_type in instrument_types:
        BoxInventory.objects.update_or_create(
            box=box,
            instrument_type=instrument_type,
            defaults={"expected_num": quantities[instrument_type.id]},
        )
