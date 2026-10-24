from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.inventory.models import InstrumentBox, InstrumentType


class Circulation(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "进行中"
        CLOSED = "CLOSED", "已关闭"

    box = models.ForeignKey(InstrumentBox, on_delete=models.PROTECT, related_name="circulations")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    outbound_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "circulation"
        indexes = [models.Index(fields=["box", "status"], name="idx_circulation_box_status")]
        constraints = [
            models.UniqueConstraint(
                fields=["box"],
                condition=Q(status="OPEN"),
                name="uq_circulation_one_open_per_box",
            ),
        ]


class CirculationItem(models.Model):
    circulation = models.ForeignKey(Circulation, on_delete=models.CASCADE, related_name="items")
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.PROTECT)
    expected_num = models.PositiveIntegerField()
    type_code_snapshot = models.CharField(max_length=64)
    display_name_snapshot = models.CharField(max_length=100)

    class Meta:
        db_table = "circulation_item"
        constraints = [
            models.UniqueConstraint(fields=["circulation", "instrument_type"], name="uq_circulation_item_type"),
        ]


class OperationRecord(models.Model):
    class OperationType(models.TextChoices):
        OUTBOUND = "OUTBOUND", "出库"
        INBOUND = "INBOUND", "入库"
        REVIEW = "REVIEW", "复核"

    class Result(models.TextChoices):
        SUCCESS = "SUCCESS", "成功"
        BUSINESS_FAILED = "BUSINESS_FAILED", "业务失败"

    operation_type = models.CharField(max_length=16, choices=OperationType.choices)
    result = models.CharField(max_length=32, choices=Result.choices)
    box = models.ForeignKey(InstrumentBox, on_delete=models.PROTECT)
    circulation = models.ForeignKey(Circulation, on_delete=models.PROTECT, null=True, blank=True)
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "operation_record"
        ordering = ["-created_at"]


class OperationRecordItem(models.Model):
    record = models.ForeignKey(OperationRecord, on_delete=models.CASCADE, related_name="items")
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.PROTECT)
    submitted_num = models.PositiveIntegerField()
    expected_num = models.PositiveIntegerField()
    diff_num = models.IntegerField()
    type_code_snapshot = models.CharField(max_length=64)
    display_name_snapshot = models.CharField(max_length=100)

    class Meta:
        db_table = "operation_record_item"
        ordering = ["type_code_snapshot"]
