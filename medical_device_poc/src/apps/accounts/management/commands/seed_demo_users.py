from __future__ import annotations

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Seed proof-of-concept login accounts from seed_data/demo_users.csv."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-file",
            default=None,
            help="CSV file containing username, password, is_staff, is_superuser, and is_active.",
        )

    def handle(self, *args, **options):
        seed_file = Path(options["seed_file"]) if options["seed_file"] else Path.cwd() / "seed_data" / "demo_users.csv"
        rows = self._read_csv(seed_file)
        User = get_user_model()

        with transaction.atomic():
            for row in rows:
                user, _created = User.objects.get_or_create(username=row["username"])
                user.set_password(row["password"])
                user.is_staff = self._parse_bool(row["is_staff"], "is_staff", row["username"])
                user.is_superuser = self._parse_bool(row["is_superuser"], "is_superuser", row["username"])
                user.is_active = self._parse_bool(row["is_active"], "is_active", row["username"])
                user.save(update_fields=["password", "is_staff", "is_superuser", "is_active"])

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(rows)} demo user(s)."))

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        required_fields = {"username", "password", "is_staff", "is_superuser", "is_active"}
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

    def _parse_bool(self, value: str, field_name: str, username: str) -> bool:
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        raise CommandError(f"demo_users.csv has invalid {field_name} for {username}: {value}")
