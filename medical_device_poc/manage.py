#!/usr/bin/env python
"""Django command-line utility for administrative tasks."""
from __future__ import annotations

import os
import sys
from pathlib import Path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
