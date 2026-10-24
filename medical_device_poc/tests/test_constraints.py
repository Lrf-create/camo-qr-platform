from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.operations.models import Circulation


def test_one_open_circulation_per_box_constraint(seeded_db):
    box = InstrumentBox.objects.get(box_code="BOX-001")
    Circulation.objects.create(box=box, status=Circulation.Status.OPEN)

    with pytest.raises(IntegrityError), transaction.atomic():
        Circulation.objects.create(box=box, status=Circulation.Status.OPEN)


def test_box_inventory_unique_box_and_type_constraint(seeded_db):
    box = InstrumentBox.objects.get(box_code="BOX-001")
    instrument_type = InstrumentType.objects.get(type_code="FORCEPS")

    with pytest.raises(IntegrityError), transaction.atomic():
        BoxInventory.objects.create(box=box, instrument_type=instrument_type, expected_num=10)
