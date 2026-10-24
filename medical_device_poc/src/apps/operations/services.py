from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.operations.models import Circulation, CirculationItem, OperationRecord, OperationRecordItem


@dataclass(frozen=True)
class QuantityLine:
    instrument_type: InstrumentType
    num: int


@dataclass(frozen=True)
class OperationResult:
    result: str
    code: str
    message: str
    record: OperationRecord


QuantityMap = dict[str, QuantityLine]


def process_outbound(box: InstrumentBox, submitted: QuantityMap) -> OperationResult:
    expected = _get_box_expected_quantities(box)

    if box.status != InstrumentBox.BoxStatus.IN_STOCK:
        return _create_business_failure(
            operation_type=OperationRecord.OperationType.OUTBOUND,
            box=box,
            circulation=None,
            submitted=submitted,
            expected=expected,
            code="INVALID_STATE",
            message=f"当前状态不允许出库：{box.status}",
        )

    if _has_quantity_diff(submitted, expected):
        return _create_business_failure(
            operation_type=OperationRecord.OperationType.OUTBOUND,
            box=box,
            circulation=None,
            submitted=submitted,
            expected=expected,
            code="QUANTITY_MISMATCH",
            message="出库器械数量与当前配置不一致",
        )

    circulation = Circulation.objects.create(box=box, status=Circulation.Status.OPEN)
    CirculationItem.objects.bulk_create(
        [
            CirculationItem(
                circulation=circulation,
                instrument_type=line.instrument_type,
                expected_num=line.num,
                type_code_snapshot=line.instrument_type.type_code,
                display_name_snapshot=line.instrument_type.display_name,
            )
            for line in expected.values()
        ]
    )

    box.status = InstrumentBox.BoxStatus.OUTBOUND
    box.save(update_fields=["status", "updated_at"])

    record = _create_record(
        operation_type=OperationRecord.OperationType.OUTBOUND,
        result=OperationRecord.Result.SUCCESS,
        box=box,
        circulation=circulation,
        message="出库成功",
        submitted=submitted,
        expected=expected,
    )
    return OperationResult(
        result=OperationRecord.Result.SUCCESS,
        code="OUTBOUND_SUCCESS",
        message="出库成功",
        record=record,
    )


def process_inbound_or_review(box: InstrumentBox, submitted: QuantityMap) -> OperationResult:
    previous_status = box.status
    operation_type = (
        OperationRecord.OperationType.REVIEW
        if previous_status == InstrumentBox.BoxStatus.INBOUND
        else OperationRecord.OperationType.INBOUND
    )

    open_circulation = (
        Circulation.objects.select_for_update()
        .filter(box=box, status=Circulation.Status.OPEN)
        .first()
    )

    if previous_status not in [InstrumentBox.BoxStatus.OUTBOUND, InstrumentBox.BoxStatus.INBOUND]:
        expected = _get_circulation_expected_quantities(open_circulation) if open_circulation else submitted
        return _create_business_failure(
            operation_type=operation_type,
            box=box,
            circulation=open_circulation,
            submitted=submitted,
            expected=expected,
            code="INVALID_STATE",
            message=f"当前状态不允许入库：{box.status}",
        )

    if open_circulation is None:
        return _create_business_failure(
            operation_type=operation_type,
            box=box,
            circulation=None,
            submitted=submitted,
            expected=submitted,
            code="OPEN_CIRCULATION_NOT_FOUND",
            message="未找到该框的开放流转记录",
        )

    expected = _get_circulation_expected_quantities(open_circulation)
    if _has_quantity_diff(submitted, expected):
        if previous_status == InstrumentBox.BoxStatus.OUTBOUND:
            box.status = InstrumentBox.BoxStatus.INBOUND
            box.save(update_fields=["status", "updated_at"])

        return _create_business_failure(
            operation_type=operation_type,
            box=box,
            circulation=open_circulation,
            submitted=submitted,
            expected=expected,
            code="QUANTITY_MISMATCH",
            message="入库器械数量与出库快照不一致",
        )

    now = timezone.now()
    box.status = InstrumentBox.BoxStatus.IN_STOCK
    box.flow_count += 1
    box.save(update_fields=["status", "flow_count", "updated_at"])

    open_circulation.status = Circulation.Status.CLOSED
    open_circulation.closed_at = now
    open_circulation.save(update_fields=["status", "closed_at"])

    _update_box_inventory(box, submitted)

    record = _create_record(
        operation_type=operation_type,
        result=OperationRecord.Result.SUCCESS,
        box=box,
        circulation=open_circulation,
        message="入库成功" if operation_type == OperationRecord.OperationType.INBOUND else "复核成功",
        submitted=submitted,
        expected=expected,
    )
    return OperationResult(
        result=OperationRecord.Result.SUCCESS,
        code="INBOUND_SUCCESS" if operation_type == OperationRecord.OperationType.INBOUND else "REVIEW_SUCCESS",
        message=record.message,
        record=record,
    )


def _get_box_expected_quantities(box: InstrumentBox) -> QuantityMap:
    inventory_rows = (
        BoxInventory.objects.select_related("instrument_type")
        .filter(box=box)
        .order_by("instrument_type__type_code")
    )
    return {
        row.instrument_type.type_code: QuantityLine(row.instrument_type, row.expected_num)
        for row in inventory_rows
    }


def _get_circulation_expected_quantities(circulation: Circulation) -> QuantityMap:
    rows = circulation.items.select_related("instrument_type").order_by("type_code_snapshot")
    return {
        row.type_code_snapshot: QuantityLine(row.instrument_type, row.expected_num)
        for row in rows
    }


def _has_quantity_diff(submitted: QuantityMap, expected: QuantityMap) -> bool:
    if set(submitted) != set(expected):
        return True
    return any(submitted[code].num != expected[code].num for code in expected)


def _create_business_failure(
    *,
    operation_type: str,
    box: InstrumentBox,
    circulation: Circulation | None,
    submitted: QuantityMap,
    expected: QuantityMap,
    code: str,
    message: str,
) -> OperationResult:
    record = _create_record(
        operation_type=operation_type,
        result=OperationRecord.Result.BUSINESS_FAILED,
        box=box,
        circulation=circulation,
        message=message,
        submitted=submitted,
        expected=expected,
    )
    return OperationResult(
        result=OperationRecord.Result.BUSINESS_FAILED,
        code=code,
        message=message,
        record=record,
    )


def _create_record(
    *,
    operation_type: str,
    result: str,
    box: InstrumentBox,
    circulation: Circulation | None,
    message: str,
    submitted: QuantityMap,
    expected: QuantityMap,
) -> OperationRecord:
    record = OperationRecord.objects.create(
        operation_type=operation_type,
        result=result,
        box=box,
        circulation=circulation,
        message=message,
    )

    items = []
    all_codes = sorted(set(submitted) | set(expected))
    for code in all_codes:
        submitted_line = submitted.get(code)
        expected_line = expected.get(code)
        line = expected_line or submitted_line
        if line is None:
            continue
        submitted_num = submitted_line.num if submitted_line else 0
        expected_num = expected_line.num if expected_line else 0
        items.append(
            OperationRecordItem(
                record=record,
                instrument_type=line.instrument_type,
                submitted_num=submitted_num,
                expected_num=expected_num,
                diff_num=submitted_num - expected_num,
                type_code_snapshot=line.instrument_type.type_code,
                display_name_snapshot=line.instrument_type.display_name,
            )
        )
    OperationRecordItem.objects.bulk_create(items)
    return record


def _update_box_inventory(box: InstrumentBox, submitted: QuantityMap) -> None:
    with transaction.atomic(savepoint=False):
        for line in submitted.values():
            BoxInventory.objects.update_or_create(
                box=box,
                instrument_type=line.instrument_type,
                defaults={"expected_num": line.num},
            )
