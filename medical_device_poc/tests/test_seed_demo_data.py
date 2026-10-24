from __future__ import annotations

from django.core.management import call_command

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.workstations.models import WorkstationControl


def test_seed_demo_data_is_repeatable(db):
    call_command("seed_demo_data", verbosity=0)
    call_command("seed_demo_data", verbosity=0)

    assert InstrumentType.objects.count() == 3
    assert InstrumentBox.objects.count() == 3
    assert BoxInventory.objects.count() == 9
    assert list(WorkstationControl.objects.order_by("port").values_list("port", "is_running")) == [
        ("A", False),
        ("B", False),
    ]
