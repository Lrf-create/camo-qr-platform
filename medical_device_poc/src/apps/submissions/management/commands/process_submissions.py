from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.submissions.services import process_all_ready_once


class Command(BaseCommand):
    help = "Poll Port A and Port B submission tables and process READY tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process all currently READY submissions once, then exit.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=settings.POLL_INTERVAL_SECONDS,
            help="Polling interval in seconds when running continuously.",
        )

    def handle(self, *args, **options):
        run_once = options["once"]
        interval = options["interval"]

        self.stdout.write("Submission polling processor started.")
        while True:
            processed = process_all_ready_once(require_running=False)
            for item in processed:
                self.stdout.write(
                    f"Port {item.port} submission {item.session_id}: "
                    f"{item.status} {item.result_code} {item.result_message}"
                )

            if run_once:
                self.stdout.write(f"Processed {len(processed)} submission(s).")
                return

            time.sleep(interval)
