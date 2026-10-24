from __future__ import annotations

from django.db import models


class InstrumentType(models.Model):
    """Instrument category recognized by external software through type_code."""

    type_code = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "instrument_type"
        ordering = ["type_code"]

    def __str__(self) -> str:
        return f"{self.type_code} - {self.display_name}"


class InstrumentBox(models.Model):
    class BoxStatus(models.TextChoices):
        IN_STOCK = "IN_STOCK", "在库"
        OUTBOUND = "OUTBOUND", "出库"
        INBOUND = "INBOUND", "入库"

    box_code = models.CharField(max_length=32, unique=True)
    box_name = models.CharField(max_length=100)
    qr_token = models.UUIDField(unique=True)
    status = models.CharField(max_length=16, choices=BoxStatus.choices, default=BoxStatus.IN_STOCK)
    flow_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "instrument_box"
        ordering = ["box_code"]

    def __str__(self) -> str:
        return f"{self.box_code} - {self.box_name}"


class BoxInventory(models.Model):
    box = models.ForeignKey(InstrumentBox, on_delete=models.PROTECT, related_name="inventory_items")
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.PROTECT)
    expected_num = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "box_inventory"
        constraints = [
            models.UniqueConstraint(fields=["box", "instrument_type"], name="uq_box_inventory_type"),
        ]
        ordering = ["box__box_code", "instrument_type__type_code"]
