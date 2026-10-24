from __future__ import annotations

import csv
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.workstations.models import WorkstationControl


class Command(BaseCommand):
    help = "Seed the small proof-of-concept inventory dataset from seed_data CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-dir",
            default=None,
            help="Directory containing instrument_types.csv, boxes.csv, and box_inventory.csv.",
        )

    def handle(self, *args, **options):
        seed_dir = Path(options["seed_dir"]) if options["seed_dir"] else Path.cwd() / "seed_data"
        instrument_rows = self._read_csv(seed_dir / "instrument_types.csv", {"code", "name"})
        box_rows = self._read_csv(seed_dir / "boxes.csv", {"display_code", "qr_token", "status", "flow_count"})
        inventory_rows = self._read_csv(seed_dir / "box_inventory.csv", {"box_code", "instrument_type", "num"})

        with transaction.atomic():
            instruments = self._upsert_instruments(instrument_rows)
            boxes = self._upsert_boxes(box_rows)
            self._upsert_inventory(inventory_rows, boxes, instruments)
            workstation_count = self._upsert_workstations()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(instruments)} instrument types, {len(boxes)} boxes, "
                f"{len(inventory_rows)} inventory rows, and {workstation_count} workstations."
            )
        )

    def _read_csv(self, path: Path, required_fields: set[str]) -> list[dict[str, str]]:
        if not path.exists():
            raise CommandError(f"Seed file not found: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            actual_fields = set(reader.fieldnames or [])
            missing_fields = required_fields - actual_fields
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise CommandError(f"Seed file {path.name} is missing fields: {missing}")

            rows = []
            for index, row in enumerate(reader, start=2):
                cleaned = {key: (value or "").strip() for key, value in row.items()}
                if not any(cleaned.values()):
                    continue
                self._validate_required_values(path.name, index, cleaned, required_fields)
                rows.append(cleaned)

        if not rows:
            raise CommandError(f"Seed file has no data rows: {path}")
        return rows

    def _validate_required_values(
        self,
        file_name: str,
        line_number: int,
        row: dict[str, str],
        required_fields: set[str],
    ) -> None:
        empty_fields = [field for field in sorted(required_fields) if not row.get(field)]
        if empty_fields:
            fields = ", ".join(empty_fields)
            raise CommandError(f"{file_name}:{line_number} has empty required fields: {fields}")

    def _upsert_instruments(self, rows: list[dict[str, str]]) -> dict[str, InstrumentType]:
        instruments = {}
        for row in rows:
            type_code = row["code"].upper()
            instrument, _created = InstrumentType.objects.update_or_create(
                type_code=type_code,
                defaults={"display_name": row["name"]},
            )
            instruments[type_code] = instrument
        return instruments

    def _upsert_boxes(self, rows: list[dict[str, str]]) -> dict[str, InstrumentBox]:
        boxes = {}
        valid_statuses = {choice.value for choice in InstrumentBox.BoxStatus}
        for row in rows:
            box_code = row["display_code"]
            status = row["status"]
            if status not in valid_statuses:
                raise CommandError(f"boxes.csv has invalid status for {box_code}: {status}")

            try:
                qr_token = uuid.UUID(row["qr_token"])
            except ValueError as exc:
                raise CommandError(f"boxes.csv has invalid qr_token for {box_code}: {row['qr_token']}") from exc

            try:
                flow_count = int(row["flow_count"])
            except ValueError as exc:
                raise CommandError(f"boxes.csv has invalid flow_count for {box_code}: {row['flow_count']}") from exc
            if flow_count < 0:
                raise CommandError(f"boxes.csv has negative flow_count for {box_code}: {flow_count}")

            box, _created = InstrumentBox.objects.update_or_create(
                box_code=box_code,
                defaults={
                    "box_name": box_code,
                    "qr_token": qr_token,
                    "status": status,
                    "flow_count": flow_count,
                },
            )
            boxes[box_code] = box
        return boxes

    def _upsert_inventory(
        self,
        rows: list[dict[str, str]],
        boxes: dict[str, InstrumentBox],
        instruments: dict[str, InstrumentType],
    ) -> None:
        seen_keys = set()
        for row in rows:
            box_code = row["box_code"]
            type_code = row["instrument_type"].upper()
            key = (box_code, type_code)
            if key in seen_keys:
                raise CommandError(f"box_inventory.csv has duplicate row: {box_code}, {type_code}")
            seen_keys.add(key)

            box = boxes.get(box_code)
            if box is None:
                raise CommandError(f"box_inventory.csv references unknown box_code: {box_code}")
            instrument = instruments.get(type_code)
            if instrument is None:
                raise CommandError(f"box_inventory.csv references unknown instrument_type: {type_code}")

            try:
                expected_num = int(row["num"])
            except ValueError as exc:
                raise CommandError(
                    f"box_inventory.csv has invalid num for {box_code}/{type_code}: {row['num']}"
                ) from exc
            if expected_num < 0:
                raise CommandError(
                    f"box_inventory.csv has negative num for {box_code}/{type_code}: {expected_num}"
                )

            BoxInventory.objects.update_or_create(
                box=box,
                instrument_type=instrument,
                defaults={"expected_num": expected_num},
            )

    def _upsert_workstations(self) -> int:
        count = 0
        for port in [WorkstationControl.Port.A, WorkstationControl.Port.B]:
            WorkstationControl.objects.update_or_create(
                port=port,
                defaults={"is_running": False},
            )
            count += 1
        return count
